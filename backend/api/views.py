from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import baseconv
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import SetPasswordSerializer
from djoser.views import UserViewSet
from rest_framework import filters, serializers, status
from rest_framework.decorators import action
from api.pagination import CustomPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from api.filters import IngredientSearch, RecipeFilter
from api.permissions import IsAdminOrReadOnly, IsAuthorOrReadOnly
from api.serializers import (AvatarSerializer, CustomUserCreateSerializer,
                             CustomUserReadSerializer, FavoriteSerializer,
                             IngredientSerializer, RecipeReadSerializer,
                             RecipeShortSerializer, RecipeWriteSerializer,
                             ShoppingCartSerializer, SubscribeSerializer,
                             TagSerializer)
from api.utils import create_or_delete_shopping_favorite
from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, Tag)
from users.models import Subscribe


User = get_user_model()


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngridientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (IngredientSearch,)
    search_fields = ('^name',)


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrReadOnly | IsAdminOrReadOnly,)
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_class = RecipeFilter
    search_fields = ('tags',)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_class(self):
        if self.action == 'retrieve' or self.action == 'list':
            return RecipeReadSerializer
        return RecipeWriteSerializer

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, **kwargs):
        return create_or_delete_shopping_favorite(
            model=ShoppingCart, pk=self.kwargs['pk'],
            serial=ShoppingCartSerializer,
            request=request, rs_serial=RecipeShortSerializer)

    @action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        user = request.user
        if not user.shopping_cart.exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        ingredients = IngredientInRecipe.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(total_amount=Sum('amount'))

        shopping_list = (
            f'Список покупок для: {user.get_full_name()}\n\n'
        )
        shopping_list += '\n'.join([
            f'- {ingredient["ingredient__name"]} '
            f'({ingredient["ingredient__measurement_unit"]})'
            f' - {ingredient["total_amount"]}'
            for ingredient in ingredients
        ])

        filename = f'{user.username}_shopping_list.txt'
        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename={filename}'

        return response

    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, **kwargs):
        return create_or_delete_shopping_favorite(
            model=Favorite, pk=self.kwargs['pk'],
            serial=FavoriteSerializer,
            request=request, rs_serial=RecipeShortSerializer)

    @action(
        methods=['get'],
        detail=True,
        url_path='get-link',
        url_name='get-link',
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        encode_id = baseconv.base64.encode(recipe.id)
        short_link = request.build_absolute_uri(
            reverse('shortlink', kwargs={'encoded_id': encode_id})
        )
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)


class ShortLinkView(APIView):

    def get(self, request, encoded_id):
        if not set(encoded_id).issubset(set(baseconv.BASE64_ALPHABET)):
            return Response(
                {'error': 'Недопустимые символы в короткой ссылке.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        recipe_id = baseconv.base64.decode(encoded_id)
        return redirect(f'/recipes/{recipe_id}/',)


class CustomUserViewSet(UserViewSet):
    serializer_class = CustomUserCreateSerializer
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return CustomUserReadSerializer
        if self.action == 'set_password':
            return SetPasswordSerializer
        if self.action == 'me':
            return CustomUserReadSerializer
        if self.action == 'create':
            return CustomUserCreateSerializer
        if self.action == 'subscribe':
            return SubscribeSerializer

    def get_permissions(self):
        if self.action in ('list', 'create', 'retrieve'):
            self.permission_classes = [AllowAny, ]
        return super().get_permissions()

    @action(methods=['post', 'delete'], detail=True)
    def subscribe(self, request, **kwargs):
        user = request.user
        author = get_object_or_404(User, id=self.kwargs['id'])
        if request.method == 'POST':
            if Subscribe.objects.filter(user=user, author=author).exists():
                raise serializers.ValidationError(
                    'Вы уже подписаны на этого автора', code=400
                )
            if user == author:
                raise serializers.ValidationError(
                    'Нельзя подписаться на самого себя', code=400
                )
            serializer = SubscribeSerializer(
                author,
                context={"request": request, }
            )
            Subscribe.objects.create(user=user, author=author)
            return Response(serializer.data, status=201)
        try:
            subscribe = Subscribe.objects.get(user=user, author=author)
            subscribe.delete()
        except Subscribe.DoesNotExist:
            raise serializers.ValidationError('Not Found', code=400)
        return Response(status=204)

    @action(methods=['get', ], detail=False,)
    def subscriptions(self, request, **kwargs):
        user = request.user
        queryset = User.objects.filter(subscribed__user=user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscribeSerializer(
            pages, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)

    @action(methods=['put', 'delete'], detail=True)
    def avatar(self, request, **kwargs):
        user = get_object_or_404(User, username=request.user)
        if request.method == 'PUT':
            serializers = AvatarSerializer(user, data=request.data)
            serializers.is_valid(raise_exception=True)
            serializers.save()
            return Response(serializers.data, status=200)
        user.avatar = None
        user.save()
        return Response(status=204)
