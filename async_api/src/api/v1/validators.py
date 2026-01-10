def validate_sort(sort: str) -> str:
    """Validate sort parameter to ensure it only contains allowed fields."""
    allowed_fields = {"imdb_rating"}

    for field in sort.split(","):
        field_name = field.lstrip("-")
        if field_name not in allowed_fields:
            raise ValueError(
                f"Invalid sort field: {field_name}, allowed fields are: {', '.join(allowed_fields)}"
            )
    return sort
