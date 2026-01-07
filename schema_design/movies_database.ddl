CREATE SCHEMA IF NOT EXISTS content;
CREATE TABLE IF NOT EXISTS content.film_work (
    id uuid PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    creation_date DATE NOT NULL,
    rating FLOAT,
    type TEXT NOT NULL,
    created TIMESTAMP WITH TIME ZONE,
    modified TIMESTAMP WITH TIME ZONE
);
CREATE TABLE IF NOT EXISTS content.genre (
    id uuid PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created TIMESTAMP WITH TIME ZONE,
    modified TIMESTAMP WITH TIME ZONE
);
CREATE TABLE IF NOT EXISTS content.person (
    id uuid PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    created TIMESTAMP WITH TIME ZONE,
    modified TIMESTAMP WITH TIME ZONE
);
CREATE TABLE IF NOT EXISTS content.person_film_work (
    id uuid PRIMARY KEY,
    film_work_id uuid NOT NULL REFERENCES content.film_work(id) ON DELETE CASCADE,
    person_id uuid NOT NULL REFERENCES content.person(id) ON DELETE CASCADE,
    role VARCHAR(255) NOT NULL,
    created TIMESTAMP WITH TIME ZONE
);
CREATE TABLE IF NOT EXISTS content.genre_film_work (
    id uuid PRIMARY KEY,
    film_work_id uuid NOT NULL REFERENCES content.film_work(id) ON DELETE CASCADE,
    genre_id uuid NOT NULL REFERENCES content.genre(id) ON DELETE CASCADE,
    created TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS film_work_title_idx ON content.film_work(title);
CREATE INDEX IF NOT EXISTS film_work_type_rating_idx ON content.film_work(type, rating);
CREATE UNIQUE INDEX IF NOT EXISTS genre_name_idx ON content.genre(name);
CREATE INDEX IF NOT EXISTS person_full_name_idx ON content.person(full_name);
CREATE UNIQUE INDEX IF NOT EXISTS film_work_person_role_idx ON content.person_film_work(film_work_id, person_id, role);
CREATE INDEX IF NOT EXISTS person_film_work_idx ON content.person_film_work(person_id, film_work_id);
CREATE UNIQUE INDEX IF NOT EXISTS genre_film_work_idx ON content.genre_film_work(genre_id, film_work_id);