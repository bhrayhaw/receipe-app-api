from core.models import (Recipe,
                         Tag,
                         Ingredients)

from rest_framework import serializers

class TagSerializer(serializers.ModelSerializer):
    """Serializer for tags"""
    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']


class IngredientSerializer(serializers.ModelSerializer):
    """Serializer for Ingredient"""
    class Meta:
        model = Ingredients
        fields = ['id', 'name']
        read_only_fields = ['id']

class RecipeSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, required=False)
    class Meta:
        model = Recipe
        fields = ['id', 'title','time_in_minutes', 'price', 'link', 'tags']
        read_only_fields = ['id']

    def _get_or_create_tags(self, tags, recipe):
        """Handling the creation or getting of a new tag"""
        auth_user = self.context['request'].user
        for tag in tags:
            tag_obj, created = Tag.objects.get_or_create(
                user=auth_user,
                **tag,
            )
            recipe.tag.add(tag_obj)


    def create(self, validated_data):
        """Create a new Recipe"""
        tags = validated_data.pop('tags', [])
        recipe = Recipe.objects.create(**validated_data)
        self._get_or_create_tags(tags, recipe)

        return recipe

    def update(self, instance, validated_data):
        """Test to update a recipe"""
        tags = validated_data.pop('tags', None)
        if tags is not None:
            instance.tag.clear()
            self._get_or_create_tags(tags, instance)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class DetailRecipeSerializer(RecipeSerializer):
    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ['description']

