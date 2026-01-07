from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass()
class DataMapper(ABC):
    id: UUID

    def __post_init__(self):
        if isinstance(self.id, str):
            self.id = UUID(self.id)

    @classmethod
    def fields_to_insert(cls) -> str:
        return ", ".join(cls.__dataclass_fields__.keys())

    @classmethod
    def s_string(cls) -> str:
        return ", ".join(["%s"] * len(cls.__dataclass_fields__))

    @classmethod
    def from_sqlite_row(cls, row_dict: dict) -> "DataMapper":
        """Create instance from SQLite row, ignoring unknown keys."""
        fields = {}
        for k, v in row_dict.items():
            if k in cls.__dataclass_fields__:
                fields[k] = v
                continue
            if k == "created_at":
                fields["created"] = v
                continue
            if k == "updated_at":
                fields["modified"] = v
                continue
        return cls(**fields)
                

    @staticmethod
    def recipient_db_schema_name() -> str:
        return "content"

    @staticmethod
    @abstractmethod
    def db_table_name() -> str: ...


@dataclass()
class FilmWork(DataMapper):
    title: str
    description: str
    rating: float
    type: str
    created: str
    modified: str
    creation_date: Optional[str] = "NOW()"

    def __post_init__(self):
        super().__post_init__()
        if not self.creation_date:
            self.creation_date = "NOW()"

    @staticmethod
    def db_table_name() -> str:
        return "film_work"

@dataclass()
class Person(DataMapper):
    full_name: str
    created: str = "NOW()"
    modified: str = "NOW()"

    @staticmethod
    def db_table_name() -> str:
        return "person"
    
@dataclass()
class Genre(DataMapper):
    name: str
    created: str
    modified: str
    description: Optional[str] = None


    @staticmethod
    def db_table_name() -> str:
        return "genre"
    
@dataclass()
class GenreFilmWork(DataMapper):
    film_work_id: UUID
    genre_id: UUID
    created: str

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.film_work_id, str):
            self.film_work_id = UUID(self.film_work_id)
        if isinstance(self.genre_id, str):
            self.genre_id = UUID(self.genre_id)

    @staticmethod
    def db_table_name() -> str:
        return "genre_film_work"
    
@dataclass()
class PersonFilmWork(DataMapper):
    film_work_id: UUID
    person_id: UUID
    role: str
    created: str

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.film_work_id, str):
            self.film_work_id = UUID(self.film_work_id)
        if isinstance(self.person_id, str):
            self.person_id = UUID(self.person_id)
            
    @staticmethod
    def db_table_name() -> str:
        return "person_film_work"