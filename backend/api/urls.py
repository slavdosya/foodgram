from django.urls import include, path
from rest_framework import routers

from api.views import (CustomUserViewSet, IngridientViewSet, RecipeViewSet,
                       TagViewSet)

router = routers.DefaultRouter()
router.register(r'tags', TagViewSet)
router.register(r'ingredients', IngridientViewSet)
router.register(r'recipes', RecipeViewSet, basename='recipes')
router.register(r'users', CustomUserViewSet)
router.register(r'users/me/avatar', CustomUserViewSet, basename='avatar')


urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
