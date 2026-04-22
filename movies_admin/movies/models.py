import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedMixin(models.Model):
    created = models.DateTimeField(_("created"), auto_now_add=True)
    modified = models.DateTimeField(_("modified"), auto_now=True)

    class Meta:
        abstract = True


class UUIDMixin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class Genre(UUIDMixin, TimeStampedMixin):
    name = models.CharField(_("name"), max_length=255, unique=True)
    description = models.TextField(_("description"), blank=True)

    def __str__(self):
        return self.name

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        db_table = 'content"."genre'
        verbose_name = _("genre")
        verbose_name_plural = _("genres")
        ordering = ["name"]  # noqa: RUF012
        indexes = [models.Index(fields=["name"], name="genre_name_idx")]  # noqa: RUF012


class FilmWorkTypeChoices(models.TextChoices):
    MOVIE = "movie", _("movie")
    TV_SHOW = "tv_show", _("tv_show")


class FilmWork(UUIDMixin, TimeStampedMixin):
    title = models.CharField(_("title"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    creation_date = models.DateField(_("creation_date"), null=True, blank=True)
    rating = models.FloatField(
        _("rating"),
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
    )
    type = models.CharField(
        _("type"),
        max_length=50,
        choices=FilmWorkTypeChoices.choices,
    )
    genres = models.ManyToManyField(
        "Genre",
        through="GenreFilmWork",
        related_name="film_works",
        verbose_name=_("genres"),
    )
    persons = models.ManyToManyField(
        "Person",
        through="PersonFilmWork",
        related_name="film_works",
        verbose_name=_("persons"),
    )

    def __str__(self):
        return f"{self.title}({self.creation_date.year if self.creation_date else ''})"

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        db_table = 'content"."film_work'
        verbose_name = _("film_work")
        verbose_name_plural = _("film_works")
        ordering = ["title"]  # noqa: RUF012
        indexes = [  # noqa: RUF012
            models.Index(fields=["title"], name="film_work_title_idx"),
            models.Index(fields=["type", "rating"], name="film_work_type_rating_idx"),
        ]


class Person(UUIDMixin, TimeStampedMixin):
    full_name = models.CharField(_("full_name"), max_length=255)

    def __str__(self):
        return self.full_name

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        db_table = 'content"."person'
        verbose_name = _("person")
        verbose_name_plural = _("persons")
        ordering = ["full_name"]  # noqa: RUF012
        indexes = [models.Index(fields=["full_name"], name="person_full_name_idx")]  # noqa: RUF012


class GenreFilmWork(UUIDMixin):
    film_work = models.ForeignKey(
        "FilmWork",
        on_delete=models.CASCADE,
        verbose_name=_("film_work"),
        related_name="genre_films",
    )
    genre = models.ForeignKey(
        "Genre",
        on_delete=models.CASCADE,
        verbose_name=_("genre"),
        related_name="genre_films",
    )
    created = models.DateTimeField(_("created"), auto_now_add=True)

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        db_table = 'content"."genre_film_work'
        verbose_name = _("genre_film_work")
        verbose_name_plural = _("genre_film_works")
        ordering = ["-created"]  # noqa: RUF012
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["genre", "film_work"],
                name="unique_genre_film_work",
            ),
        ]


class PersonFilmWork(UUIDMixin):
    film_work = models.ForeignKey(
        "FilmWork",
        on_delete=models.CASCADE,
        verbose_name=_("film_work"),
        related_name="person_films",
    )
    person = models.ForeignKey(
        "Person",
        on_delete=models.CASCADE,
        verbose_name=_("person"),
        related_name="person_films",
    )
    role = models.CharField(_("role"), max_length=255)
    created = models.DateTimeField(_("created"), auto_now_add=True)

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        db_table = 'content"."person_film_work'
        verbose_name = _("person_film_work")
        verbose_name_plural = _("person_film_works")
        ordering = ["-created"]  # noqa: RUF012
        indexes = [  # noqa: RUF012
            models.Index(
                fields=["film_work", "person", "role"],
                name="film_work_person_role_idx",
            ),
            models.Index(
                fields=["person", "film_work"],
                name="person_film_work_idx",
            ),
        ]
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["film_work", "person", "role"],
                name="unique_film_work_person_role",
            ),
        ]
