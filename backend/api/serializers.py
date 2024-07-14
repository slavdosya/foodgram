from django.contrib.auth import get_user_model
from django.db.models import F
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField

from api.fields import Base64ImageField
from api.utils import bulk_create_ingredients
from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, Tag)
from users.models import Subscribe

User = get_user_model()


class CustomUserCreateSerializer(UserCreateSerializer):
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)

    class Meta:
        model = User
        fields = (
            'username', 'id', 'email', 'password',
            'first_name', 'last_name',
        )

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already exists')
        return value


class CustomUserReadSerializer(UserSerializer):
    is_subscribed = SerializerMethodField(read_only=True)
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = (
            'username', 'id', 'email',
            'first_name', 'last_name', 'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Subscribe.objects.filter(user=user, author=obj).exists()

    def update(self, instance, validated_data):
        instance.avatar = validated_data.get('avatar')
        instance.save()
        return instance


class SubscribeSerializer(CustomUserReadSerializer):
    recipes = SerializerMethodField()
    is_subscribed = serializers.BooleanField(default=False)
    recipes_count = SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'username', 'id', 'email', 'first_name',
            'last_name', 'is_subscribed', 'recipes', 'recipes_count', 'avatar'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        recipes = obj.recipes.all()
        if limit:
            recipes = recipes[:int(limit)]
        serializer = RecipeShortSerializer(recipes, many=True, read_only=True)
        return serializer.data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)


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
        if value is None:
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
        recipe.tags.set(tags)
        bulk_create_ingredients(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        instance.ingredients.clear()
        bulk_create_ingredients(ingredients, instance)
        instance.tags.clear()
        instance.tags.set(tags)
        return super().update(instance, validated_data)

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
            amount=F('ingredient_list__amount')
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
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Favorite
        fields = ('id', 'recipe', 'user')


class ShoppingCartSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShoppingCart
        fields = ('id', 'recipe', 'user')
