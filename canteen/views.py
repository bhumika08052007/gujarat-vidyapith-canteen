from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
import logging
from decimal import Decimal
import razorpay
import urllib.parse
from .models import FoodItem, Order, OrderItem

logger = logging.getLogger(__name__)

FOOD_IMAGE_PATHS = {
    "chai": "canteen/images/chai.jpg",
    "Coffee": "canteen/images/Coffee.jpg",
    "Vegetable Sandwich": "canteen/images/Vegetable Sandwich.jpg",
    "Aloo Butter Sandwich": "canteen/images/Aloo Butter Sandwich.jpg",
    "Cheese and Jam Sandwich": "canteen/images/Cheese and Jam Sandwich.jpg",
    "Poha": "canteen/images/Poha.jpg",
    "Veg Pakoda": "canteen/images/Veg Pakoda.jpg",
    "Kachori-Samosa": "canteen/images/Kachori-Samosa.jpg",
    "Vada Pav": "canteen/images/Vada Pav.jpg",
    "Dabeli": "canteen/images/Dabeli.jpg",
    "Khaman Dhokla": "canteen/images/Khaman Dhokla.jpg",
    "Thepla": "canteen/images/Thepla.jpg",
    "Aloo Paratha": "canteen/images/Aloo Paratha.jpg",
    "Jalebi": "canteen/images/Jalebi.jpg",
    "Plain Dosa-Sambar": "canteen/images/Plain Dosa-Sambar.jpg",
    "Masala Dosa-Sambar": "canteen/images/Masala Dosa-Sambar.jpg",
    "Idli-Sambar (2 pcs)": "canteen/images/Idli-Sambar (2 pcs).jpg",
    "Medu Vada-Sambar (2 pcs)": "canteen/images/Medu Vada-Sambar (2 pcs).jpg",
    "Puri-Sabji (4 pcs)": "canteen/images/puri shbaji.jpg",
    "Lassi": "canteen/images/Lassi.jpg",
    "Chhas": "canteen/images/chaas.jpg",
    "Fixed Thali": "canteen/images/Fixed Thali.jpg",
    "Unlimited Thali": "canteen/images/Unlimited Thali.jpg",
}


def _add_static_food_images(menu_items):
    for item in menu_items:
        item.static_image = FOOD_IMAGE_PATHS.get(item.name)
    return menu_items


def home(request):
    menu_items = _add_static_food_images(
        FoodItem.objects.filter(is_available=True)
    )

    return render(
        request,
        "canteen/home.html",
        {"menu_items": menu_items}
    )


def menu(request):
    menu_items = _add_static_food_images(
        FoodItem.objects.all().order_by("id")
    )

    return render(
        request,
        "canteen/menu.html",
        {"menu_items": menu_items}
    )


def about(request):
    return render(request, "canteen/about.html")


def contact(request):
    return render(request, "canteen/contact.html")


# ADD TO CART
def add_to_cart(request, item_id):

    item = get_object_or_404(FoodItem, id=item_id)

    if item.stock > 0 and item.is_available:

        cart = request.session.get("cart", {})

        item_id = str(item_id)

        cart[item_id] = cart.get(item_id, 0) + 1

        request.session["cart"] = cart

    return redirect("cart")


# CART
def cart(request):

    cart_data = request.session.get("cart", {})

    cart_items = []

    total = 0

    for item_id, quantity in cart_data.items():

        item = get_object_or_404(FoodItem, id=item_id)
        item.static_image = FOOD_IMAGE_PATHS.get(item.name)

        item_total = item.price * quantity

        cart_items.append({
            "item": item,
            "quantity": quantity,
            "total": item_total
        })

        total += item_total

    return render(
        request,
        "canteen/cart.html",
        {
            "cart_items": cart_items,
            "grand_total": total
        }
    )


# REMOVE FROM CART
def remove_from_cart(request, item_id):

    cart_data = request.session.get("cart", {})

    item_id = str(item_id)

    if item_id in cart_data:

        del cart_data[item_id]

    request.session["cart"] = cart_data

    return redirect("cart")


# CHECKOUT
@login_required(login_url="login")
def checkout(request):

    cart_data = request.session.get("cart", {})

    if not cart_data:

        return redirect("cart")

    cart_items = []

    total = Decimal("0.00")

    for item_id, quantity in cart_data.items():
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            messages.error(request, "Your cart has an invalid quantity. Please update it and try again.")
            return redirect("cart")

        if quantity < 1:
            messages.error(request, "Your cart has an invalid quantity. Please update it and try again.")
            return redirect("cart")

        item = get_object_or_404(FoodItem, id=item_id)
        item.static_image = FOOD_IMAGE_PATHS.get(item.name)

        item_total = item.price * quantity

        cart_items.append({
            "item": item,
            "quantity": quantity,
            "total": item_total
        })

        total += item_total

    if request.method == "POST":

        customer_name = request.POST.get("customer_name", "").strip()
        customer_email = request.POST.get("customer_email", "").strip()

        if not customer_name:
            customer_name = request.user.first_name.strip()
        if not customer_email:
            customer_email = request.user.email.strip()

        if len(customer_name) < 2:
            messages.error(request, "Please enter a valid name with at least 2 characters.")
            return redirect("checkout")

        try:
            validate_email(customer_email)
        except ValidationError:
            messages.error(request, "Please enter a valid email address.")
            return redirect("checkout")

        try:
            with transaction.atomic():
                order_total = Decimal("0.00")
                for cart_item in cart_items:
                    food = FoodItem.objects.select_for_update().get(
                        id=cart_item["item"].id
                    )
                    if not food.is_available or cart_item["quantity"] > food.stock:
                        raise ValidationError(
                            f"{food.name} is no longer available in the requested quantity. "
                            "Please update your cart."
                        )
                    cart_item["item"] = food
                    cart_item["total"] = food.price * cart_item["quantity"]
                    order_total += cart_item["total"]

                order = Order.objects.create(
                    user=request.user,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    payment_method="Pay at Counter (Cash)",
                    total_amount=order_total,
                    status="Pending",
                    stock_reserved=True,
                )

                for cart_item in cart_items:
                    food = cart_item["item"]
                    OrderItem.objects.create(
                        order=order,
                        food_item=food,
                        food_name=food.name,
                        price=food.price,
                        quantity=cart_item["quantity"],
                        total_price=food.price * cart_item["quantity"],
                    )
                    food.stock -= cart_item["quantity"]
                    food.save(update_fields=("stock",))
        except ValidationError as exc:
            messages.error(
                request,
                exc.messages[0] if exc.messages else "The order could not be saved. Please try again.",
            )
            return redirect("checkout")
        except FoodItem.DoesNotExist:
            messages.error(request, "A food item in your cart no longer exists. Please update your cart.")
            return redirect("checkout")

        request.session.pop("cart", None)
        request.session.pop("checkout_data", None)
        request.session["latest_order_id"] = order.id
        return redirect("order_success")

    return render(
        request,
        "canteen/checkout.html",
        {
            "cart_items": cart_items,
            "grand_total": total
        }
    )


# AUTHENTICATION
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)
        if user is not None:
            auth_login(request, user)
            messages.success(request, "Logged in successfully!")
            return redirect("checkout")
        else:
            messages.error(request, "Invalid email or password.")
            return redirect("login")

    return render(
        request,
        "canteen/login.html",
        {"active_form": "login"}
    )


def register_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("register")
        else:
            # We use email for username since username is required
            user = User.objects.create_user(username=email, email=email, password=password, first_name=name)
            messages.success(request, "Registration successful. Please login.")
            return redirect("login")

    return render(
        request,
        "canteen/login.html",
        {"active_form": "register"}
    )


def logout_view(request):
    auth_logout(request)
    return redirect("home")


def _save_order_from_session(request, payment_method, razorpay_order_id=None, razorpay_payment_id=None):
    checkout_data = request.session.get("checkout_data", {})
    cart_data = request.session.get("cart", {})

    total = Decimal(str(checkout_data.get("total", "0")))
    customer_name = (
        checkout_data.get("customer_name")
        or (request.user.first_name if request.user.is_authenticated else "Customer")
    )
    customer_email = (
        checkout_data.get("customer_email")
        or (request.user.email if request.user.is_authenticated else "")
    )

    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        customer_name=customer_name,
        customer_email=customer_email,
        payment_method=payment_method,
        total_amount=total,
        status="Pending",
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
    )

    for item_id, quantity in cart_data.items():
        try:
            food = FoodItem.objects.get(id=item_id)
            OrderItem.objects.create(
                order=order,
                food_item=food,
                food_name=food.name,
                price=food.price,
                quantity=quantity,
                total_price=food.price * quantity,
            )
        except (FoodItem.DoesNotExist, ValueError):
            continue

    return order


@login_required(login_url="login")
def order_success(request):
    order_id = request.session.pop("latest_order_id", None)
    order = None
    if order_id:
        try:
            order = Order.objects.prefetch_related("items").get(id=order_id)
        except Order.DoesNotExist:
            pass

    if not order and request.user.is_authenticated:
        order = Order.objects.filter(user=request.user).prefetch_related("items").first()

    return render(
        request,
        "canteen/order_success.html",
        {"payment_method": "cash", "order": order}
    )


# PAYMENT SYSTEM REMOVED - Redirect legacy routes to checkout or order history
def payment(request):
    return redirect("checkout")


def payment_success(request):
    return redirect("order_history")


# ORDER HISTORY
@login_required(login_url="login")
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')

    for o in orders:
        o.can_cancel = o.status == 'Pending'
        for item in o.items.all():
            item.static_image = FOOD_IMAGE_PATHS.get(item.food_name)

    return render(
        request,
        "canteen/order_history.html",
        {"orders": orders}
    )


@login_required(login_url="login")
def order_status_updates(request):
    orders = Order.objects.filter(user=request.user).values('id', 'status')
    return JsonResponse({
        'orders': [
            {'id': order['id'], 'status': order['status']}
            for order in orders
        ],
    })


@login_required(login_url="login")
def cancel_order(request, order_id):
    if request.method != "POST":
        return redirect("order_history")

    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status != "Pending":
        messages.error(
            request,
            "Order is already being prepared or is no longer eligible for cancellation.",
        )
    elif order.cancel():
        messages.success(request, f"Order #{order.id} cancelled successfully.")
    else:
        messages.error(request, "This order can no longer be cancelled.")

    return redirect("order_history")


def gpay_payment(request):
    return redirect("checkout")