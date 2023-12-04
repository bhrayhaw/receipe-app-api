from decimal import Decimal

import tempfile
import os

from PIL import Image

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse


from core.models import (Recipe,
                         Tag,
                         Ingredients)
from recipe.serializers import (RecipeSerializer,
                                DetailRecipeSerializer)

from rest_framework.test import APIClient
from rest_framework import status


RECIPE_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    """Create and return an image url"""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def create_recipe(user, **params):
    defaults = {
        'title': 'Sample Recipe',
        'description': 'Sample Recipe Description',
        'time_in_minutes': 60,
        'price': Decimal('32.34'),
        'link': 'http://example.com/sample.pdf'
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(RECIPE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITest(TestCase):
    def setUp(self):
        self.user = create_user(
            email='user@example.com',
            password='password',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_recipe(self):
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_limited_to_user(self):
        other_user = create_user(
            email='otheruser@example.com',
            password='otheruser123',
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)
        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_detail_recipe(self):
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)

        res = self.client.get(url)
        serializer = DetailRecipeSerializer(recipe)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        payload = {
            'title': 'Sample Recipe',
            'time_in_minutes': 20,
            'price': Decimal('30.90')
        }
        res = self.client.post(RECIPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        original_link = 'http://example.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe',
            link=original_link,
        )
        payload = {'title': 'New Title'}

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        recipe = create_recipe(
            user=self.user,
            title='Sample Recipe',
            description='Sample Recipe description',
            link='http://example.com/recipe.pdf',
        )
        payload = {
            'title': 'New Recipe',
            'description': 'New Sample Recipe description',
            'time_in_minutes': 30,
            'price': Decimal('45.90'),
            'link': 'http://example.com/new_recipe.pdf',
        }

        url = detail_url(recipe.id)
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_recipe_user_returns_error(self):
        new_user = create_user(
            email="newuser@example.com", password="newpassword")
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)
        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_recipe_by_other_user_error(self):
        new_user = create_user(
            email="newuser@example.com", password="password")
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        """Test creating a new recipe with new tags"""
        payload = {
            'title': 'Sample Title',
            'time_in_minutes': 30,
            'price': Decimal('30.89'),
            'tags': [{'name': 'Dessert'}, {'name': 'Dinner'}]
        }
        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tag.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tag.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tag(self):
        """Test for creating a recipe with an existing tag"""
        tag_gh = Tag.objects.create(user=self.user, name='Jollof')
        payload = {
            'title': 'Jollof Recipe',
            'time_in_minutes': 50,
            'price': Decimal('120.00'),
            'tags': [{'name': 'Jollof'}, {'name': 'Lunch'}]
        }
        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tag.count(), 2)
        self.assertIn(tag_gh, recipe.tag.all())
        for tag in payload['tags']:
            exists = recipe.tag.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """Test create tag on update"""
        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        self.assertIn(new_tag, recipe.tag.all())

    def test_update_recipe_assign_tag(self):
        """Test to assign an existing tag when updating"""
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tag.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {'tags': [{'name': 'Lunch'}]}

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tag.all())
        self.assertNotIn(tag_breakfast, recipe.tag.all())

    def test_clear_recipe_tags(self):
        """Test to clear the tags of a recipe"""
        tag = Tag.objects.create(user=self.user, name="Lunch")
        recipe = create_recipe(user=self.user)
        recipe.tag.add(tag)

        payload = {'tags': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tag.count(), 0)

    def test_create_recipe_with_new_ingredients(self):
        """Test to create recipe with ingredient"""
        payload = {
            'title': 'Sample Recipe',
            'time_in_minutes': 30,
            'price': Decimal('23.09'),
            'description': 'Sample Description',
            'link': 'https://example.com/recipe.pdf',
            'tags': [
                {'name': 'Dessert'},
                {'name': 'Dinner'},
            ],
            'ingredients': [
                {'name': 'Corn Dough'},
                {'name': 'Cassava Dough'}
            ]
        }
        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                user=self.user,
                name=ingredient['name']
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredients(self):
        """Test to create a recipe with existing ingredients"""
        ingredient_new = Ingredients.objects.create(
            user=self.user, name='Pepper')
        payload = {
            'title': 'Sample Recipe',
            'time_in_minutes': 30,
            'price': Decimal('23.09'),
            'description': 'Sample Description',
            'link': 'https://example.com/recipe.pdf',
            'tags': [
                {'name': 'Dessert'},
                {'name': 'Dinner'},
            ],
            'ingredients': [
                {'name': 'Pepper'},
                {'name': 'Cassava Dough'}
            ]
        }
        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient_new, recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """Test to update an existing ingredient"""
        recipe = create_recipe(user=self.user)

        payload = {'ingredients': [{'name': 'Bread and Egg'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredients.objects.get(
            user=self.user, name='Bread and Egg')
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_assign_existing_ingredient_when_update(self):
        """Test updating an existing ingredient in the recipe"""
        ingredient_main = Ingredients.objects.create(
            user=self.user, name='Bread and Egg')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient_main)

        ingredient_brunch = Ingredients.objects.create(
            user=self.user, name='Tomato')
        payload = {'ingredients': [{'name': 'Tomato'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient_brunch, recipe.ingredients.all())
        self.assertNotIn(ingredient_main, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """Test to clear the ingredients of a recipe"""
        ingredient = Ingredients.objects.create(
            user=self.user, name="Lunch")
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {'ingredients': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filtering_recipe_with_tags(self):
        """Filter recipe with tags"""
        r1 = create_recipe(user=self.user, title='Chicken Soup')
        r2 = create_recipe(user=self.user, title='Goat light Soup')
        r3 = create_recipe(user=self.user, title='Cow light Soup')
        tag1 = Tag.objects.create(user=self.user, name='Spicy')
        tag2 = Tag.objects.create(user=self.user, name='Best Soup')
        r1.tag.add(tag1)
        r2.tag.add(tag2)

        params = {'tags': f'{tag1.id}, {tag2.id}'}
        res = self.client.get(RECIPE_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filtering_recipe_with_ingredient(self):
        """Test for filtering recipe with an Ingredient"""
        r1 = create_recipe(user=self.user, title='Chicken Soup')
        r2 = create_recipe(user=self.user, title='Goat light Soup')
        r3 = create_recipe(user=self.user, title='Cow light Soup')
        ingredient1 = Ingredients.objects.create(
            user=self.user, name='Chicken')
        ingredient2 = Ingredients.objects.create(user=self.user, name='Goat')
        r1.ingredients.add(ingredient1)
        r2.ingredients.add(ingredient2)

        params = {'ingredients': f'{ingredient1.id}, {ingredient2.id}'}
        res = self.client.get(RECIPE_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTest(TestCase):
    """Test for image upload API"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'test123'
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_image_upload(self):
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, 'JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.recipe.refresh_from_db()
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))
