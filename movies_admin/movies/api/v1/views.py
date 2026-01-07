from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Q, QuerySet
from rest_framework.viewsets import ReadOnlyModelViewSet

from movies.api.v1.pagination import MoviePagination
from movies.api.v1.serializers import MovieSerializer
from movies.models import FilmWork


class MoviesViewSet(ReadOnlyModelViewSet):
    serializer_class = MovieSerializer
    pagination_class = MoviePagination

    def get_queryset(self) -> QuerySet[FilmWork]:
        return FilmWork.objects.annotate(
            genres_names=ArrayAgg(
                "genres__name",
                distinct=True,
                default=[],
            ),
            actors_names=ArrayAgg(
                "persons__full_name",
                filter=Q(person_films__role="actor"),
                distinct=True,
                default=[],
            ),
            directors_names=ArrayAgg(
                "persons__full_name",
                filter=Q(person_films__role="director"),
                distinct=True,
                default=[],
            ),
            writers_names=ArrayAgg(
                "persons__full_name",
                filter=Q(person_films__role="writer"),
                distinct=True,
                default=[],
            ),
        )
