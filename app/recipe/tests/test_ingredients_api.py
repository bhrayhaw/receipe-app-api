"""Tests for the Ingredients API"""
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (Recipe, Ingredients)

from recipe.serializers import IngredientSerializer, RecipeSerializer

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

    def test_update_ingredient(self):
        """Test to update an existing ingredient"""
        ingredient = create_ingredient(user=self.user, name="Corn Dough")
        payload = {"name": "Cassava Dough"}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload["name"])

    def test_delete_ingredient(self):
        """Test deleting an ingredient"""
        ingredient = create_ingredient(user=self.user)
        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        ingredients = Ingredients.objects.filter(user=self.user)
        self.assertFalse(ingredients.exists())

    def test_filtering_ingredients_assigned_to_recipes(self):
        """Test to list filtered ingredients assigned to recipes"""
        ing1 = create_ingredient(user=self.user, name='Corn')
        ing2 = create_ingredient(user=self.user, name='Cassava Dough')
        recipe1 = Recipe.objects.create(
            title='Banku',
            time_in_minutes=40,
            price=Decimal('10.00'),
            user=self.user
        )
        recipe1.ingredients.add(ing1)

        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(ing1)
        s2 = IngredientSerializer(ing2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_are_unique(self):
        """Test for checking uniqueness of filtered ingredients"""
        ing = create_ingredient(user=self.user, name='Kontomire')
        create_ingredient(user=self.user, name='Garden Eggs')
        recipe1 = Recipe.objects.create(
            title='Palava Sauce',
            time_in_minutes=40,
            price=Decimal('30.00'),
            user=self.user,
        )
        recipe2 = Recipe.objects.create(
            title='Garden Egg Stew',
            time_in_minutes=45,
            price=Decimal('30.00'),
            user=self.user,
        )
        recipe1.ingredients.add(ing)
        recipe2.ingredients.add(ing)

        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
