"""
Tests for Tags API
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework.test import APIClient
from rest_framework import status

from core.models import (Recipe, Tag)

from recipe.serializers import TagSerializer

TAG_URL = reverse('recipe:tag-list')

def create_user(email="user@example.com", password="password123"):
    """Create and return new user"""
    return get_user_model().objects.create_user(email=email, password=password)

def create_tag(user, **params):
    """Create and return new tag"""
    default = {
        'name': 'Sample Tag',
    }
    default.update(params)

    tag = Tag.objects.create(user=user, **default)
    return tag

def detail_url(tag_id):
    """URL for a specific tag"""
    return reverse('recipe:tag-detail', args=[tag_id])

class PublicTagsAPITest(TestCase):
    """Test unauthenticated API requests"""
    def setUp(self):
        self.client = APIClient()

    def test_authentication_required(self):
        """Test auth is required for retrieving tags"""
        res = self.client.get(TAG_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsAPITest(TestCase):
    """Test for authenticated API requests"""
    def setUp(self):
        self.user = create_user()
        self.client = APIClient()

        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """Test to retrieve a list of tags"""
        create_tag(user=self.user, name="Vegan")
        create_tag(user=self.user, name="Dessert")

        res = self.client.get(TAG_URL)
        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test tags are limited to authenticated user"""
        new_user = create_user(email="newuser@example.com")
        create_tag(user=new_user, name="Fruity")
        tag = Tag.objects.create(user=self.user, name="Veggies")

        res = self.client.get(TAG_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)

    def test_to_update_tag(self):
        """Test for updating a tag"""
        tag = create_tag(user=self.user, name="Barbecue")
        payload = {
            'name': 'Continental'
        }
        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        """Test for deleting a tag"""
        tag = create_tag(user=self.user)
        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        #tags = Tag.objects.filter(user=self.user)
        #self.assertFalse(tags.exists())
        self.assertFalse(Tag.objects.filter(id=tag.id).exists())

    def test_filtering_tags_assigned_to_recipes(self):
        """Test to list filtered tags"""
        tag1 = create_tag(user=self.user, name='stew')
        tag2 = create_tag(user=self.user, name='dinner')
        recipe1 = Recipe.objects.create(
            title='Palava Sauce',
            time_in_minutes=34,
            price=Decimal('40.00'),
            user=self.user
        )
        recipe1.tag.add(tag1)

        res = self.client.get(TAG_URL, {'assigned_only': 1})

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_tags_are_unique(self):
        """Test the uniqueness of filtered tags"""
        tag = create_tag(user=self.user, name='Veges')
        create_tag(user=self.user, name='dinner')
        recipe1 = Recipe.objects.create(
            title='Banku',
            time_in_minutes=45,
            price=Decimal('34.00'),
            user=self.user,
        )
        recipe2 = Recipe.objects.create(
            title='Fufu',
            time_in_minutes=45,
            price=Decimal('34.00'),
            user=self.user,
        )

        recipe1.tag.add(tag)
        recipe2.tag.add(tag)

        res = self.client.get(TAG_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)