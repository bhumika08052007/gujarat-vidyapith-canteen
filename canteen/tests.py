from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from .models import FoodItem, Order, OrderItem


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
        self.assertContains(response, 'href="/login/"')
        self.assertContains(response, 'href="/register/"')

    def test_home_page_uses_static_food_image(self):
        FoodItem.objects.create(name="chai", price=10, stock=10, is_available=True)

        response = self.client.get("/")

        self.assertContains(response, "/static/canteen/images/chai.jpg")

    def test_home_page_shows_logout_link_when_authenticated(self):
        user = User.objects.create_user(
            username="customer@example.com",
            email="customer@example.com",
            password="safe-test-password",
        )
        self.client.force_login(user)

        response = self.client.get("/")

        self.assertContains(response, 'href="/logout/"')
        self.assertNotContains(response, 'href="/login/"')


class MenuPageTests(TestCase):
    def test_menu_page_uses_static_food_image(self):
        FoodItem.objects.create(
            name="Vegetable Sandwich",
            price=40,
            stock=5,
            is_available=True,
        )

        response = self.client.get(reverse("menu"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "/static/canteen/images/Vegetable%20Sandwich.jpg",
        )


class CheckoutFlowTests(TestCase):
    def setUp(self):
        self.item = FoodItem.objects.create(
            name="Tea",
            price=15,
            stock=10,
            is_available=True,
        )
        self.user = User.objects.create_user(
            username="customer@example.com",
            email="customer@example.com",
            password="safe-test-password",
            first_name="Customer",
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["cart"] = {str(self.item.id): 1}
        session.save()

    def test_login_page_is_reachable(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email Login")
        self.assertContains(response, "Create Account")
        self.assertEqual(response.context["active_form"], "login")

    def test_register_url_opens_combined_page_with_register_selected(self):
        response = self.client.get(reverse("register"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email Login")
        self.assertContains(response, "Create Account")
        self.assertEqual(response.context["active_form"], "register")

    def test_login_accepts_email_and_password(self):
        self.client.logout()

        response = self.client.post(
            reverse("login"),
            {"email": "customer@example.com", "password": "safe-test-password"},
        )

        self.assertRedirects(response, reverse("checkout"), fetch_redirect_response=False)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_checkout_page_is_reachable_with_cart(self):
        response = self.client.get(reverse("checkout"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Checkout")
        self.assertContains(response, "Place Order")

    def test_checkout_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse("checkout"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('checkout')}",
        )

    def test_cart_shows_items_and_order_summary(self):
        response = self.client.get(reverse("cart"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your items")
        self.assertContains(response, "Tea")
        self.assertContains(response, "Order summary")
        self.assertContains(response, "₹15.00")
        self.assertContains(response, reverse("checkout"))

    def test_empty_cart_shows_menu_link(self):
        session = self.client.session
        session["cart"] = {}
        session.save()

        response = self.client.get(reverse("cart"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your cart is empty")
        self.assertContains(response, reverse("menu"))

    def test_direct_checkout_creates_order_and_reaches_success(self):
        response = self.client.post(
            reverse("checkout"),
            {
                "customer_name": "Customer",
                "customer_email": "customer@example.com",
            },
        )

        self.assertRedirects(response, reverse("order_success"), fetch_redirect_response=False)
        response = self.client.get(reverse("order_success"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Order Successful!")
        order = Order.objects.get()
        self.assertEqual(order.total_amount, self.item.price)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.get().food_item, self.item)
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock, 9)
        self.assertNotIn("cart", self.client.session)

    def test_customer_can_cancel_pending_order_and_stock_is_restored_once(self):
        self.client.post(
            reverse("checkout"),
            {
                "customer_name": "Customer",
                "customer_email": "customer@example.com",
            },
        )
        order = Order.objects.get()
        cancel_url = reverse("cancel_order", args=[order.id])

        response = self.client.post(cancel_url)

        self.assertRedirects(response, reverse("order_history"), fetch_redirect_response=False)
        order.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(order.status, "Cancelled")
        self.assertEqual(self.item.stock, 10)

        self.client.post(cancel_url)
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock, 10)

    def test_customer_cannot_cancel_after_preparation_starts(self):
        self.item.stock = 9
        self.item.save(update_fields=["stock"])
        order = Order.objects.create(
            user=self.user,
            customer_name="Customer",
            customer_email="customer@example.com",
            payment_method="Pay at Counter (Cash)",
            total_amount=15,
            status="Preparing",
        )
        OrderItem.objects.create(
            order=order,
            food_item=self.item,
            food_name=self.item.name,
            price=self.item.price,
            quantity=1,
            total_price=self.item.price,
        )

        self.client.post(reverse("cancel_order", args=[order.id]))

        order.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(order.status, "Preparing")
        self.assertEqual(self.item.stock, 9)

    def test_customer_cannot_cancel_another_users_order(self):
        other_user = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="safe-test-password",
        )
        order = Order.objects.create(
            user=other_user,
            customer_name="Other Customer",
            customer_email="other@example.com",
            payment_method="Pay at Counter (Cash)",
            total_amount=15,
        )

        response = self.client.post(reverse("cancel_order", args=[order.id]))

        self.assertEqual(response.status_code, 404)

    def test_order_status_updates_are_private_to_the_logged_in_customer(self):
        own_order = Order.objects.create(
            user=self.user,
            customer_name="Customer",
            customer_email="customer@example.com",
            payment_method="Pay at Counter (Cash)",
            total_amount=15,
            status="Ready",
        )
        other_user = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="safe-test-password",
        )
        Order.objects.create(
            user=other_user,
            customer_name="Other Customer",
            customer_email="other@example.com",
            payment_method="Pay at Counter (Cash)",
            total_amount=30,
        )

        response = self.client.get(reverse("order_status_updates"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"orders": [{"id": own_order.id, "status": "Ready"}]},
        )

    def test_checkout_rejects_quantity_above_available_stock(self):
        self.item.stock = 0
        self.item.save(update_fields=["stock"])

        response = self.client.post(
            reverse("checkout"),
            {
                "customer_name": "Customer",
                "customer_email": "customer@example.com",
            },
        )

        self.assertRedirects(response, reverse("checkout"), fetch_redirect_response=False)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.client.session["cart"], {str(self.item.id): 1})

    def test_order_history_handles_deleted_food_item(self):
        order = Order.objects.create(
            user=self.user,
            customer_name="Customer",
            customer_email="customer@example.com",
            payment_method="Pay at Counter (Cash)",
            total_amount=15,
        )
        OrderItem.objects.create(
            order=order,
            food_item=None,
            food_name="Removed item",
            price=15,
            quantity=1,
            total_price=15,
        )

        response = self.client.get(reverse("order_history"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Removed item")

    def test_legacy_payment_routes_redirect_safely(self):
        response = self.client.get(reverse("payment"))
        self.assertRedirects(response, reverse("checkout"))

        response_gpay = self.client.get(reverse("gpay_payment"))
        self.assertRedirects(response_gpay, reverse("checkout"))


class CanteenAdminTests(TestCase):
    def setUp(self):
        admin_user = User.objects.create_superuser(
            username="canteen-admin",
            email="admin@example.com",
            password="safe-test-password",
        )
        self.client.force_login(admin_user)
        self.food = FoodItem.objects.create(
            name="Tea",
            price=15,
            stock=8,
        )
        self.order = Order.objects.create(
            customer_name="Customer",
            customer_email="customer@example.com",
            payment_method="Pay at Counter (Cash)",
            total_amount=15,
            stock_reserved=True,
        )
        OrderItem.objects.create(
            order=self.order,
            food_item=self.food,
            food_name=self.food.name,
            price=self.food.price,
            quantity=1,
            total_price=self.food.price,
        )

    def test_food_order_and_order_item_admin_pages_are_available(self):
        food_response = self.client.get(
            reverse("admin:canteen_fooditem_changelist")
        )
        order_response = self.client.get(
            reverse("admin:canteen_order_changelist")
        )
        item_response = self.client.get(
            reverse("admin:canteen_orderitem_changelist")
        )

        self.assertEqual(food_response.status_code, 200)
        self.assertContains(food_response, "/static/canteen/admin.css")
        self.assertContains(food_response, "Tea")
        self.assertEqual(order_response.status_code, 200)
        self.assertContains(order_response, "status-badge status-pending")
        self.assertContains(order_response, "Pay at Counter (Cash)")
        self.assertEqual(item_response.status_code, 200)
        self.assertContains(item_response, "Tea")

    def test_admin_can_cancel_orders_and_restore_stock(self):
        response = self.client.post(
            reverse("admin:canteen_order_changelist"),
            {
                "action": "cancel_orders",
                "_selected_action": str(self.order.id),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.food.refresh_from_db()
        self.assertEqual(self.order.status, "Cancelled")
        self.assertEqual(self.food.stock, 9)

    def test_low_stock_filter_lists_food_below_the_alert_threshold(self):
        FoodItem.objects.create(name="Low stock tea", price=10, stock=5)

        response = self.client.get(
            reverse("admin:canteen_fooditem_changelist"),
            {"stock_level": "low"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Low stock tea")
        self.assertContains(response, "Low stock: 5")

    def test_food_item_price_is_checked_by_the_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FoodItem.objects.create(
                    name="Invalid item",
                    price=-1,
                    stock=1,
                )
