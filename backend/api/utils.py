from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from api.error import ValidationError404
from recipes.models import IngredientInRecipe, Recipe


def bulk_create_ingredients(ingredients, recipe):
    bulk_list = []
    for ingredient in ingredients:

        bulk_list.append(
            IngredientInRecipe(
                recipe=recipe,
                ingredient_id=ingredient.get('id'),
                amount=ingredient.get('amount'))
        )
    return IngredientInRecipe.objects.bulk_create(bulk_list)


def create_or_delete_shopping_favorite(model, request, pk, serial, rs_serial):
    user = request.user
    if request.method == 'POST':
        try:
            recipe = Recipe.objects.get(pk=pk)
        except Recipe.DoesNotExist:
            raise ValidationError404('Recipe does not exist')
        if model.objects.filter(user=user, recipe=recipe).exists():
            raise ValidationError('Вы уже добавили этот рецепт')
        data = {
            'user': request.user.id,
            'recipe': recipe.id
        }
        serializer = serial(data=data)
        if serializer.is_valid():
            serializer.save()
            serializer_recipe = rs_serial(recipe)
            return Response(serializer_recipe.data, status=201)
        return Response(serializer.errors, status=400)
    recipe = get_object_or_404(Recipe, pk=pk)
    obj = model.objects.filter(user=user, recipe=recipe)
    if obj.exists():
        obj.delete()
        return Response(status=204)
    raise ValidationError('Вы не добавили этот рецепт')
