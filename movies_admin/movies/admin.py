from django.contrib import admin

from .models import FilmWork, Genre, GenreFilmWork, Person, PersonFilmWork


class GenreFilmWorkInline(admin.TabularInline):
    fields = ("genre",)
    autocomplete_fields = ("genre",)
    model = GenreFilmWork
    extra = 1


class PersonFilmWorkInline(admin.TabularInline):
    fields = (
        "person",
        "role",
    )
    autocomplete_fields = ("person",)
    model = PersonFilmWork
    extra = 1


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ("name", "description", "created", "modified")
    search_fields = ("id", "name", "description")


@admin.register(FilmWork)
class FilmWorkAdmin(admin.ModelAdmin):
    inlines = (GenreFilmWorkInline, PersonFilmWorkInline)
    save_on_top = True
    list_display = ("title", "type", "creation_date", "rating", "created", "modified")
    list_filter = ("type", "genres")
    search_fields = ("id", "title", "description")
    readonly_fields = ("id", "created", "modified")
    fields = (
        "id",
        "title",
        "description",
        "creation_date",
        "type",
        "rating",
        "created",
        "modified",
    )


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    inlines = (PersonFilmWorkInline,)
    save_on_top = True
    list_display = ("full_name", "created", "modified")
    search_fields = ("id", "full_name")
