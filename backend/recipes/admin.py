from django.contrib import admin

from recipes.models import (
    Tag, Ingredient, Recipe, RecipeTag,
    IngredientInRecipe, ShoppingCart, Favorite
    )


class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'slug',)


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit',)


# class RecipeAdmin(admin.ModelAdmin):
#     list_display = ('id', 'name', 'author', 'tags', 'ingredients')
#     list_filter = ('author', 'name', 'tags')


class RecipeTagAdmin(admin.ModelAdmin):
    list_display = ('tag', 'recipe')


class IngredientInRecipeAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')


class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')


class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')


admin.site.register(Tag, TagAdmin)
admin.site.register(Ingredient, IngredientAdmin)
# admin.site.register(Recipe, RecipeAdmin)
admin.site.register(RecipeTag, RecipeTagAdmin)
admin.site.register(IngredientInRecipe, IngredientInRecipeAdmin)
admin.site.register(ShoppingCart, ShoppingCartAdmin)
admin.site.register(Favorite, FavoriteAdmin)
