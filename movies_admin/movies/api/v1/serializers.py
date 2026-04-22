from rest_framework.serializers import CharField, ListField, ModelSerializer

from movies.models import FilmWork


class MovieSerializer(ModelSerializer):
    genres = ListField(child=CharField(), source="genres_names")
    actors = ListField(child=CharField(), source="actors_names")
    directors = ListField(child=CharField(), source="directors_names")
    writers = ListField(child=CharField(), source="writers_names")

    class Meta:
        model = FilmWork
        fields = (
            "id",
            "title",
            "description",
            "creation_date",
            "rating",
            "type",
            "genres",
            "actors",
            "directors",
            "writers",
        )
        read_only_fields = fields
