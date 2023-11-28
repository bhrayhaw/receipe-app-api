from rest_framework import (viewsets,
                            mixins,)
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from recipe import serializers
from core.models import (Recipe,
                         Tag,
                         Ingredients)


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.DetailRecipeSerializer
    queryset = Recipe.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user).order_by('-id')

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.RecipeSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TagViewSet(mixins.ListModelMixin,
                 mixins.UpdateModelMixin,
                 mixins.DestroyModelMixin,
                 viewsets.GenericViewSet):
    """Manage Tags in the database."""
    serializer_class = serializers.TagSerializer
    queryset = Tag.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user).order_by('-name')


class IngredientViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Manage Ingredients in the database"""
    serializer_class = serializers.IngredientSerializer
    queryset = Ingredients.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user).order_by('-name')
