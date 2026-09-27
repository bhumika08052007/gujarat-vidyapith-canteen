from django.test import TestCase

from .models import FoodItem


class HomePageTests(TestCase):
    def test_home_page_lists_available_food_items(self):
        FoodItem.objects.create(name="Tea", price=15, stock=10, is_available=True)
        FoodItem.objects.create(name="Samosa", price=20, stock=5, is_available=True)
        FoodItem.objects.create(name="Burger", price=35, stock=0, is_available=False)

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tea")
        self.assertContains(response, "Samosa")
        self.assertNotContains(response, "Burger")
