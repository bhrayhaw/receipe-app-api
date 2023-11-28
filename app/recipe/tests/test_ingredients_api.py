"""Tests for the Ingredients API"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (Recipe, Ingredients)

from recipe.serializers import IngredientSerializer

INGREDIENT_URL = reverse('recipe:ingredients-list')

def detail_url(ingredient_id):
    return reverse('recipe:ingredients-detail', args=[ingredient_id])


def create_ingredient(user, **params):
    """Create and return new ingredient"""
    default = {
        'name': 'Sample Ingredient',
    }
    default.update(params)

    ingredient = Ingredients.objects.create(user=user, **default)
    return ingredient


def create_user(email="user@example.com", password="password123"):
    return get_user_model().objects.create_user(email=email, password=password)


class PublicIngredientAPITest(TestCase):
    """Test case for public users."""
    def setUp(self):
        self.client = APIClient()

    def test_user_unauthorized(self):
        """Test user_unauthorized"""
        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientAPITest(TestCase):
    """Test case for private users."""
    def setUp(self):
        self.client = APIClient()
        self.user = create_user()

        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """Test to retrieve a list of ingredients"""
        create_ingredient(user=self.user, name="Ingredient1")
        create_ingredient(user=self.user, name="Ingredient12")

        res = self.client.get(INGREDIENT_URL)
        ingredients = Ingredients.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_tags_limited_to_user(self):
        """Test ingredients are limited to authenticated user"""
        new_user = create_user(email="newuser@example.com")
        create_ingredient(user=new_user, name="Fruity")
        ingredient = Ingredients.objects.create(user=self.user, name="Veggies")

        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

