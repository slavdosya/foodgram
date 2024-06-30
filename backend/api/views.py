from django.shortcuts import get_object_or_404
from django.urls import reverse
from api.serializers import (
    TagSerializer, IngredientSerializer, RecipeWriteSerializer,
    RecipeReadSerializer, RecipeShortSerializer, FavoriteSerializer
)
from api.filters import RecipeFilter
from recipes.models import Tag, Ingredient, Recipe, ShoppingCart, Favorite
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from django.http import FileResponse, HttpResponseRedirect
from django.utils import baseconv


from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.serializers import ValidationError
from rest_framework import filters
from rest_framework import status
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from api.permissions import IsAuthorOrReadOnly, IsAdminOrReadOnly


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngridientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('name',)


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

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, **kwargs):
        user = request.user
        if request.method == 'POST':
            try:
                recipe = Recipe.objects.get(pk=self.kwargs['pk'])
            except Recipe.DoesNotExist:
                raise ValidationError('Recipe does not exist', code=400)
            serializer = RecipeShortSerializer(recipe)
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                raise ValidationError('Товар уже существует в корзине')
            ShoppingCart.objects.create(user=user, recipe=recipe)
            return Response(serializer.data, status=201)
        if request.method == 'DELETE':
            recipe = get_object_or_404(Recipe, pk=self.kwargs['pk'])
            try:
                shopping_cart = ShoppingCart.objects.get(
                    user=user, recipe=recipe
                )
            except ShoppingCart.DoesNotExist:
                raise ValidationError('Товар не найден', code=404)
            shopping_cart.delete()
            return Response(status=204)

    @action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        user = request.user
        shopping_cart = ShoppingCart.objects.filter(user=user)

        pdf_file = "shopping_cart.pdf"
        pdf = canvas.Canvas(pdf_file)
        pdfmetrics.registerFont(TTFont('ArialUnicode', 'arial.ttf'))
        pdf.setFont("ArialUnicode", 12)
        pdf.drawString(100, 800, "Продуктовая корзина:")
        y_position = 780
        for obj in shopping_cart:
            ingredients = obj.recipe.ingredients.all()
            for ingredient in ingredients:
                pdf.drawString(100, y_position, ingredient.name)
                y_position -= 20
        pdf.save()
        return FileResponse(open(pdf_file, 'rb'), as_attachment=True, filename='shopping_cart.pdf')

    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, **kwargs):
        if request.method == 'POST':
            try:
                recipe = Recipe.objects.get(pk=self.kwargs['pk'])
            except Recipe.DoesNotExist:
                raise ValidationError('Товар не найден', code=400)
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
        if request.method == 'DELETE':
            recipe = get_object_or_404(Recipe, pk=self.kwargs['pk'])
            favorite = Favorite.objects.filter(
                user=request.user, recipe=recipe
            )
            if favorite.exists():
                favorite.delete()
                return Response(status=204)
            raise ValidationError('Товар не найден', code=404)

    # Кодирование сокращенной ссылки

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

# Декодирование сокращенной ссылки
class ShortLinkView(APIView):

    def get(self, request, encoded_id):
        if not set(encoded_id).issubset(set(baseconv.BASE64_ALPHABET)):
            return Response(
                {'error': 'Недопустимые символы в короткой ссылке.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        recipe_id = baseconv.base64.decode(encoded_id)
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        return HttpResponseRedirect(
            request.build_absolute_uri(
                f'/api/recipes/{recipe.id}/'
            )
        )
