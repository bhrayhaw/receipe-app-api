from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from core import models

def create_user(email='user@example.com', password='password'):
    return get_user_model().objects.create_user(email, password)


class ModelTestCase(TestCase):
    def test_for_email_login(self):
        email="test@example.com"
        password="testpassword"
        user=get_user_model().objects.create_user(
            email=email,
            password=password
        )
        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_for_normalized_email(self):
        list_of_emails = [
            ["test@EXAMPLE.com", "test@example.com"],
            ["TEST@EXAMPLE.COM", "TEST@example.com"],
            ["Test@Example.com", "Test@example.com"],
            ["test2@example.COM", "test2@example.com"],
        ]
        for email, expected in list_of_emails:
            user = get_user_model().objects.create_user(email, "sample123")
            self.assertEqual(user.email, expected)

    def test_for_user_without_email_to_raise_error(self):
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', 'test1234')

    def test_for_superuser(self):
        user = get_user_model().objects.create_superuser('test@example.com', 'test123')

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_recipe(self):
        user = get_user_model().objects.create_user(
            email='user@example.com',
            password='password',
        )
        recipe = models.Recipe.objects.create(
            user=user,
            title="Sample recipe",
            description="Sample recipe description",
            time_in_minutes=5,
            price=Decimal('10.30'),
        )

        self.assertEqual(str(recipe), recipe.title)

    def test_create_tags(self):
        user = create_user()
        tag = models.Tag.objects.create(user=user, name='Tag1')

        self.assertEqual(str(tag), tag.name)

    def test_create_ingredient(self):
        user = create_user()
        ingredient = models.Ingredients.objects.create(
            user=user,
            name='Ingredient1'
        )

        self.assertEqual(str(ingredient), ingredient.name)