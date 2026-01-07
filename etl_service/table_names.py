import enum


class TableNames(enum.Enum):
    """
    Enumeration of table names used in the database schema.

    This enum provides a centralized way to reference database table names
    throughout the ETL service, ensuring consistency and reducing the risk
    of typos or mismatches.

    Attributes:
        PERSON (str): The 'person' table containing information about people
            (e.g., actors, directors, writers).
        GENRE (str): The 'genre' table containing film genre classifications.
        FILM_WORK (str): The 'film_work' table containing information about
            films and other media works.
    """

    PERSON = "person"
    GENRE = "genre"
    FILM_WORK = "film_work"
