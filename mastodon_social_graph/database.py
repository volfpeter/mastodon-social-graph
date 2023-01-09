from graphscraper.db import GraphDatabaseInterface, create_graph_database_interface


class MastodonSocialGraphDatabaseFactories:
    """
    Database interface factories for `MastodonSocialGraph`.
    """

    @classmethod
    def sqlite_memory_database(cls) -> GraphDatabaseInterface:
        """
        Creates an in-memory SQLite database interface.
        """
        return cls._make_database(engine_url="sqlite://")

    @classmethod
    def sqlite_file_database(
        cls,
        *,
        engine_url: str = "sqlite:///mastodon-social-graph.db",
        clean: bool = False,
    ) -> GraphDatabaseInterface:
        """
        Creates an SQLite file database interface.

        Arguments:
            engine_url: Database URL, e.g. "sqlite:///my-filename.db".
            clean: Whether to wipe the database if it already exists.
        """
        return cls._make_database(engine_url=engine_url, clean=clean)

    @classmethod
    def _make_database(
        cls,
        *,
        engine_url: str,
        clean: bool = False,
    ) -> GraphDatabaseInterface:
        """
        Creates the default database interface for the graph.

        Arguments:
            engine_url: The URL of the database to use.
            clean: Whether to wipe the database if it already exists.
        """
        import sqlalchemy
        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy.orm import relationship, sessionmaker
        from sqlalchemy.pool import StaticPool

        Base = declarative_base()
        engine = sqlalchemy.create_engine(
            engine_url,
            poolclass=StaticPool,
        )
        Session = sessionmaker(bind=engine)
        database: GraphDatabaseInterface = create_graph_database_interface(
            sqlalchemy,
            Session(),
            Base,
            relationship,
        )

        if clean:
            Base.metadata.drop_all(engine)

        Base.metadata.create_all(engine)

        return database
