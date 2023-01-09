# mastodon-social-graph

Mastodon social graph with an SQL backend, in-memory cache, and built-in, on-demand web scraper.

## Installation

You can install the library and all its dependencies using `pip install mastodon-social-graph`.

## Getting started

### 1) Register your application to get an access token

Log in to the Mastodon instance you would like the graph to work with and register a new application in the Preferences / Development menu.

Alternatively, you can use `Mastodon.py` to create an application. You can start [here](https://mastodonpy.readthedocs.io/en/stable/).

### 2) Create a Mastodon (`Mastodon.py`) instance

You can create a `Mastodon` instance like this:

```Python
from mastodon import Mastodon

mastodon_app = Mastodon(
    access_token="<your-application's-acces-token>",
    api_base_url="<mastodon-server-url>",  # E.g. https://mastodon.social
    ratelimit_method="wait",  # Wait when you hit the rate limit.
)
```

For other options, see `Mastodon.py`'s [documentation](https://mastodonpy.readthedocs.io/en/stable/).

### 3) Create the graph

If you already have `mastodon_app` -- created in the previous step -- in scope, you can create the graph like this:

```Python
from mastodon_social_graph import MastodonSocialGraph

graph = MastodonSocialGraph(mastodon_app)
```

### 4) Load a node and its neighbors

Once you have the `graph`, you can load the first node from Mastodon like this:

```Python
account_name: str = "mastodon"

mastodon_account_node = graph.get_node_for_account_name(account_name)
if mastodon_account_node is None:
    raise ValueError("Node not found.")

# This call fetches neighbor nodes in the background if they are not stored already locally.
# If the neighbors of the node are already in the database, no request will be sent to Mastodon.
neighbors = mastodon_account_node.neighbors
for node in neighbors:
    # `node.external_id` is the account handle, `node.name` is the Mastodon database ID (for technical reasons).
    print(f"{node.external_id} ({node.name})")
```

For configuration, utilities, and details, please see the code.

## Notice

Use this library and the fetched data responsibly.

The Mastodon API is rate limited and paged. Certain methods (e.g. follower loading) of the graph -- and its build-in web scraper -- can result in a large number of requests towards the Mastodon instance. These methods can be quite slow, because by design the web scraper makes only 1 request at a time and it doesn't try to work around the imposed rate limit.

## Dependencies

The library is built on [graphscraper](https://pypi.org/project/graphscraper/) and [Mastodon.py](https://pypi.org/project/Mastodon.py/), and under the hood `graphscraper` works with an SQL (by default SQLite) database.

## Development

Use `black` for code formatting and `mypy` for static code analysis.

## Contributing

Contributions are welcome, but keep in mind this is a hobby project intended for light Mastodon social network analysis and discovery.

## License - MIT

The library is open-sourced under the conditions of the MIT [license](https://choosealicense.com/licenses/mit/).
