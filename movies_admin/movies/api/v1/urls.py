from rest_framework.routers import DefaultRouter

from movies.api.v1.views import MoviesViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r"movies", MoviesViewSet, basename="movies")

urlpatterns = [
    *router.urls,
]
