from django.urls import include, path
from rest_framework import routers

from api.views import IngridientViewSet, RecipeViewSet, TagViewSet

router = routers.DefaultRouter()
router.register(r'tags', TagViewSet)
router.register(r'ingredients', IngridientViewSet)
router.register(r'recipes', RecipeViewSet, basename='recipes')


urlpatterns = [
    path('', include(router.urls)),
]
