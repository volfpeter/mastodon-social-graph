from __future__ import annotations
import logging

from graphscraper.base import Graph, Node, NodeList
from graphscraper.db import GraphDatabaseInterface
from mastodon import Mastodon, MastodonNotFoundError

from .database import MastodonSocialGraphDatabaseFactories


class MastodonSocialGraph(Graph):
    """
    Mastodon social graph.

    Node class: `MastodonSocialGraphNode`.
    """

    def __init__(
        self,
        mastodon: Mastodon,
        *,
        database: GraphDatabaseInterface | None = None,
        followers: bool = False,
        following: bool = True,
        swallow_errors: bool = True,
    ) -> None:
        """
        Initialization.

        Arguments:
            mastodon: The `Mastodon` instance to use to interact with the server.
            database: The `GraphDatabaseInterface` to use. If `None`,
                      a default sqlite database will be used.
            followers: Whether to treat follower accounts as connections. `False` by default,
                       don't turn it on unless your application is not rate limited by the server.
            following: Whether to treat followed accounts as connections. Default value is `True`.
            swallow_errors: Whether to swallow `Mastodon.py` errors, like `MastodonNotFound`.
        """
        super().__init__(database or MastodonSocialGraphDatabaseFactories.sqlite_file_database())
        self._followers = followers
        self._following = following
        self._logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        self._mastodon = mastodon
        self._swallow_errors = swallow_errors

        self._configure_logger()

    def _configure_logger(self) -> None:
        """
        Configures the logger of the graph.
        """
        self._logger.setLevel(logging.DEBUG)
        handler: logging.Handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter("%(levelname)s | %(asctime)s | %(name)s\n -- %(message)s"))
        self._logger.addHandler(handler)

    def _create_node_list(self) -> NodeList:
        """
        Inherited.
        """
        return MastodonSocialGraphNodeList(self)

    def get_account_for_account_name(self, account_name: str) -> dict | None:
        """
        Returns the `account dict` (see Mastodon.py) for the account that matches the given name, if there is one.

        If multiple matches are found or there are no matching accounts at all, `None` will be returned.

        Arguments:
            account_name: The name (Mastodon handle without the instance part) of the account to look up.
        """
        accounts: list[dict] = self._mastodon.account_search(account_name)

        # Only 1 match?
        if len(accounts) == 1:
            return accounts[0]

        # Multiple matches, is there an exact one?
        matches = [a for a in accounts if a["acct"] == account_name]
        if len(matches) == 1:
            return matches[0]

        # Still nothing - is there a case-insensitive exact match?
        lower_account_name = account_name.lower()
        matches = [a for a in accounts if a["acct"].lower() == lower_account_name]
        if len(matches) == 1:
            return matches[0]

        return None

    def get_authentic_node_name(self, node_name: str) -> str | None:
        """
        Returns the correct node name for the given value if the name refers a unique node.

        Arguments:
            node_name: The node name, in this case the account's Mastodon database ID.
        """
        return node_name.strip()

    def get_node_for_account_name(self, account_name: str) -> MastodonSocialGraphNode | None:
        """
        Returns the graph node corresponding to the given account name, if the account exists.

        If the node does not exists yet but it refers a unique Mastodon account,
        a graph node will automatically be created.

        Arguments:
            account_name: The name of the account.
        """
        account = self.get_account_for_account_name(account_name)
        if account is None:
            return None

        return self.nodes.get_node_by_name(
            str(account["id"]),
            can_validate_and_load=True,
            external_id=account["acct"],
        )

    def load_follower_accounts(self, account_id: str) -> list[dict]:
        """
        Loads and returns "follower accounts" data from Mastodon for the account with the given ID.

        Warning: because of the paging on the Mastodon API, this method could trigger a large number
        of requests, which could take a lot of time to complete because of API's rate limiting.

        Arguments:
            account_id: The Mastodon database account ID.

        Returns:
            List of `account dict`s (see Mastodon.py docs).
        """
        try:
            return self._mastodon.fetch_remaining(self._mastodon.account_followers(account_id))
        except MastodonNotFoundError as e:
            self._logger.error(f"Account was not found: {account_id}")
            if self._swallow_errors:
                return []

            raise e

    def load_following_accounts(self, account_id: str) -> list[dict]:
        """
        Loads and returns "following accounts" data from Mastodon for the account with the given ID.

        Arguments:
            account_id: The Mastodon database account ID.

        Returns:
            List of `account dict`s (see Mastodon.py docs).
        """
        try:
            return self._mastodon.fetch_remaining(self._mastodon.account_following(account_id))
        except MastodonNotFoundError as e:
            self._logger.error(f"Account was not found: {account_id}")
            if self._swallow_errors:
                return []

            raise e

    def load_neighbor_accounts(self, account_id: str) -> list[dict]:
        """
        Returns the "neighbor" accounts of the Mastodon account with the given database ID.

        Arguments:
            account_id: The Mastodon database account ID.

        Returns:
            List of `account dict`s (see Mastodon.py docs).
        """
        followers = self.load_follower_accounts(account_id) if self._followers else []
        following = self.load_following_accounts(account_id) if self._following else []
        return [*followers, *following]


class MastodonSocialGraphNode(Node):
    """
    Mastodon social graph node.

    Attributes:
        name: Mastodon database ID.
        external_id: Account name.
    """

    def load_follower_accounts(self) -> list[dict]:
        """
        Loads and returns "follower accounts" data from Mastodon for this node.

        Returns:
            List of `account dict`s (see Mastodon.py docs).
        """
        graph: MastodonSocialGraph = self._graph
        return graph.load_follower_accounts(self.name)

    def load_following_accounts(self) -> list[dict]:
        """
        Loads and returns "following accounts" data from Mastodon for this node.

        Returns:
            List of `account dict`s (see Mastodon.py docs).
        """
        graph: MastodonSocialGraph = self._graph
        return graph.load_following_accounts(self.name)

    def _load_neighbors_from_external_source(self) -> None:
        """
        Inherited.
        """
        # We can return if the account belongs to a different Mastodon instance.
        if "@" in self.name:
            return

        graph: MastodonSocialGraph = self._graph
        nodes: MastodonSocialGraphNodeList = graph.nodes

        accounts = graph.load_neighbor_accounts(self.name)
        for account in accounts:
            mastodon_id: str = str(account["id"])
            account_name: str = account["acct"]
            at_index = account_name.find("@")
            instance_postfix = "" if at_index == -1 else account_name[at_index:]

            neighbor = nodes.get_node_by_name(
                (
                    mastodon_id.strip() + instance_postfix
                ),  # Add the instance postfix to the name (Mastodon DB ID) to mark external nodes.
                can_validate_and_load=True,
                external_id=account_name,
            )

            if neighbor is not None:
                graph.add_edge(self, neighbor)


class MastodonSocialGraphNodeList(NodeList):
    """
    `NodeList` that produces `MastodonSocialGraphNode` instances.
    """

    def _create_node(self, index: int, name: str, external_id: str | None = None) -> Node:
        """
        Inherited.
        """
        return MastodonSocialGraphNode(
            graph=self._graph,
            index=index,
            name=name,
            external_id=external_id,
        )
