from core.models import Recipe

from rest_framework import serializers


class RecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ['id', 'title','time_in_minutes', 'price', 'link']
        read_only_fields = ['id']


class DetailRecipeSerializer(RecipeSerializer):
    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields.append('description')