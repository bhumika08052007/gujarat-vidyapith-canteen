from django.shortcuts import render, redirect, get_object_or_404
from .models import FoodItem


def home(request):
    menu_items = FoodItem.objects.filter(is_available=True)

    return render(request, "canteen/home.html", {
        "menu_items": menu_items
    })


def menu(request):
    menu_items = FoodItem.objects.all().order_by("id")

    return render(request, "canteen/menu.html", {
        "menu_items": menu_items
    })


def about(request):
    return render(request, "canteen/about.html")


def contact(request):
    return render(request, "canteen/contact.html")


def add_to_cart(request, item_id):
    item = get_object_or_404(FoodItem, id=item_id)

    if item.stock > 0:
        cart = request.session.get("cart", {})

        item_id = str(item_id)

        cart[item_id] = cart.get(item_id, 0) + 1

        request.session["cart"] = cart

    return redirect("cart")


def cart(request):
    cart_data = request.session.get("cart", {})

    cart_items = []
    total = 0

    for item_id, quantity in cart_data.items():

        item = get_object_or_404(FoodItem, id=item_id)

        item_total = item.price * quantity

        cart_items.append({
            "item": item,
            "quantity": quantity,
            "total": item_total
        })

        total += item_total

    return render(request, "canteen/cart.html", {
        "cart_items": cart_items,
        "grand_total": total
    })


def remove_from_cart(request, item_id):

    cart_data = request.session.get("cart", {})

    item_id = str(item_id)

    if item_id in cart_data:
        del cart_data[item_id]

    request.session["cart"] = cart_data

    return redirect("cart")