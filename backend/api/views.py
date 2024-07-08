from django.db.models import Sum
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import baseconv
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from api.error import ValidationError404
from api.filters import IngredientSearch, RecipeFilter
from api.permissions import IsAdminOrReadOnly, IsAuthorOrReadOnly
from api.serializers import (FavoriteSerializer, IngredientSerializer,
                             RecipeReadSerializer, RecipeShortSerializer,
                             RecipeWriteSerializer, TagSerializer)
from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, Tag)

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.serializers import SetPasswordSerializer
from djoser.views import UserViewSet
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from users.models import Subscribe
from api.serializers import (AvatarSerializer, CustomUserCreateSerializer,
                             CustomUserReadSerializer, SubscribeSerializer)

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
    pagination_class = LimitOffsetPagination
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_class = RecipeFilter
    search_fields = ('tags',)

    def get_queryset(self):
        queryset = Recipe.objects.all()
        in_shopping_cart = self.request.query_params.get('is_in_shopping_cart')
        if in_shopping_cart == '1':
            shopping_cart_ids = ShoppingCart.objects.all().values_list(
                'recipe_id',
            )
            shopping_cart_list = Recipe.objects.filter(
                id__in=shopping_cart_ids
            )
            return shopping_cart_list
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_class(self):
        if self.action == 'retrieve' or self.action == 'list':
            return RecipeReadSerializer
        return RecipeWriteSerializer

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, **kwargs):
        user = request.user
        if request.method == 'POST':
            try:
                recipe = Recipe.objects.get(pk=self.kwargs['pk'])
            except Recipe.DoesNotExist:
                raise ValidationError404('Recipe does not exist')
            serializer = RecipeShortSerializer(recipe)
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                raise ValidationError('Товар уже существует в корзине')
            ShoppingCart.objects.create(user=user, recipe=recipe)
            return Response(serializer.data, status=201)
        recipe = get_object_or_404(Recipe, pk=self.kwargs['pk'])
        try:
            shopping_cart = ShoppingCart.objects.get(user=user, recipe=recipe)
        except ShoppingCart.DoesNotExist:
            raise ValidationError('Товар не найден', code=404)
        shopping_cart.delete()
        return Response(status=204)

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
        ).annotate(amount=Sum('amount'))

        shopping_list = (
            f'Список покупок для: {user.get_full_name()}\n\n'
        )
        shopping_list += '\n'.join([
            f'- {ingredient["ingredient__name"]} '
            f'({ingredient["ingredient__measurement_unit"]})'
            f' - {ingredient["amount"]}'
            for ingredient in ingredients
        ])

        filename = f'{user.username}_shopping_list.txt'
        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename={filename}'

        return response

    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, **kwargs):
        if request.method == 'POST':
            try:
                recipe = Recipe.objects.get(pk=self.kwargs['pk'])
            except Recipe.DoesNotExist:
                raise ValidationError404('Товар не найден')
            if Favorite.objects.filter(
                user=request.user, recipe=recipe
            ).exists():
                raise ValidationError('Товар уже существует в избранном')
            data = {
                'user': request.user.id,
                'recipe': recipe.id
            }
            serializer = FavoriteSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                serializer_recipe = RecipeShortSerializer(recipe)
                return Response(serializer_recipe.data, status=201)
            return Response(serializer.errors, status=400)
        recipe = get_object_or_404(Recipe, pk=self.kwargs['pk'])
        favorite = Favorite.objects.filter(user=request.user, recipe=recipe)
        if favorite.exists():
            favorite.delete()
            return Response(status=204)
        raise ValidationError('Товар не найден', code=404)

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
        return redirect('recipes-detail', pk=recipe_id)


'''
=====================================
User views
=====================================
'''


class CustomUserViewSet(UserViewSet):
    serializer_class = CustomUserCreateSerializer
    pagination_class = LimitOffsetPagination

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
