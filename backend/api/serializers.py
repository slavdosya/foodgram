from django.shortcuts import get_object_or_404
from django.db.models import F
from rest_framework import serializers
from rest_framework.exceptions import ValidationError


from recipes.models import (
    Tag, Ingredient, Recipe, IngredientInRecipe, RecipeTag, Favorite
)
from users.serializers import CustomUserReadSerializer

import base64

from django.core.files.base import ContentFile


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='recipe.' + ext)

        return super().to_internal_value(data)



class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientInRecipeWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount')


class RecipeWriteSerializer(serializers.ModelSerializer):
    ingredients = IngredientInRecipeWriteSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    author = CustomUserReadSerializer(read_only=True)
    image = Base64ImageField(required=True, allow_null=True)

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
            'author'
        )

    def validate_ingredients(self, value):
        if 'ingredients' not in self.initial_data:
            raise ValidationError({
                'ingredients': 'Нужен хотя бы один ингредиент!'
            })
        if len(value) == 0:
            raise ValidationError('Нужен хотя бы один ингредиент!')
        ingrediens_list = []
        for val in value:
            try:
                ingredient = Ingredient.objects.get(id=val['id'])
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError('Ингредиент не найден!')
            if ingredient in ingrediens_list:
                raise ValidationError('Ингредиент не должны повторятся!')
            ingrediens_list.append(ingredient)
            if val['amount'] <= 0:
                raise ValidationError(
                    'Количество ингредиента должно быть больше 0!'
                )
        return value

    def validate_tags(self, value):
        if len(value) == 0:
            raise ValidationError('Нужен хотя бы один тег!')
        tag_list = []
        for val in value:
            if val in tag_list:
                raise ValidationError('Тег не должен повторятся!')
            tag_list.append(val)
        return value

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        for tag in tags:
            RecipeTag.objects.create(recipe=recipe, tag=tag)
        for ingredient in ingredients:
            ingredient_id = ingredient.get('id')
            ingredient_obj = get_object_or_404(
                Ingredient.objects.all(), pk=ingredient_id
            )
            amount = ingredient.get('amount')
            IngredientInRecipe.objects.create(
                recipe=recipe, ingredient=ingredient_obj, amount=amount
            )
        return recipe

    def update(self, instance, validated_data):
        if 'ingredients' not in validated_data:
            raise ValidationError({
                'ingredients': 'Нужен хотя бы один ингредиент!'
            })
        if 'tags' not in validated_data:
            raise ValidationError({
                'tags': 'Нужен хотя бы один тег!'
            })
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance.ingredients.clear()
        for ingredient in ingredients:
            IngredientInRecipe.objects.create(
                recipe=instance,
                ingredient=get_object_or_404(
                    Ingredient.objects.all(), pk=ingredient['id']
                ),
                amount=ingredient['amount']
            )
        instance.tags.clear()
        instance.tags.set(tags)
        instance.save()
        return instance

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        return RecipeReadSerializer(instance, context=context).data


class RecipeReadSerializer(serializers.ModelSerializer):
    author = CustomUserReadSerializer(read_only=True)
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)
    tags = TagSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
            'is_favorited',
            'is_in_shopping_cart'
        )

    def get_ingredients(self, obj):
        ingredients = obj.ingredients.values(
            'id',
            'name',
            'measurement_unit',
            amount=F('ingredientlist__amount')
        )
        return ingredients

    def get_is_favorited(self, instance):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return user.favorites.filter(recipe=instance).exists()

    def get_is_in_shopping_cart(self, instance):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return user.shopping_cart.filter(recipe=instance).exists()


class RecipeShortSerializer(serializers.ModelSerializer):
    image = serializers.CharField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Favorite
        fields = ('id', 'recipe', 'user')

class UrlSerializer(serializers.Serializer):
    pass