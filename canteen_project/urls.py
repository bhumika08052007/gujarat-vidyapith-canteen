from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from canteen import views


urlpatterns = [

    # Admin
    path("admin/", admin.site.urls),

    # Home
    path("", views.home, name="home"),

    # Menu
    path("menu/", views.menu, name="menu"),

    # About
    path("about/", views.about, name="about"),

    # Contact
    path("contact/", views.contact, name="contact"),

    # Cart
    path("cart/", views.cart, name="cart"),

    path(
        "cart/add/<int:item_id>/",
        views.add_to_cart,
        name="add_to_cart"
    ),

    path(
        "cart/remove/<int:item_id>/",
        views.remove_from_cart,
        name="remove_from_cart"
    ),

    # Checkout
    path(
        "checkout/",
        views.checkout,
        name="checkout"
    ),

    # Login
    path(
        "login/",
        views.login_view,
        name="login"
    ),

    # Register
    path(
        "register/",
        views.register_view,
        name="register"
    ),

    # Logout
    path(
        "logout/",
        views.logout_view,
        name="logout"
    ),

    # Payment
    path(
        "payment/",
        views.payment,
        name="payment"
    ),

    # Google Pay / UPI Payment
    path(
        "payment/gpay/",
        views.gpay_payment,
        name="gpay_payment"
    ),

    # Payment Success
    path(
        "payment-success/",
        views.payment_success,
        name="payment_success"
    ),

    # Order Success
    path(
        "order-success/",
        views.order_success,
        name="order_success"
    ),

    # Order History
    path(
        "orders/",
        views.order_history,
        name="order_history"
    ),
    path(
        "orders/status/",
        views.order_status_updates,
        name="order_status_updates"
    ),
    path(
        "orders/<int:order_id>/cancel/",
        views.cancel_order,
        name="cancel_order"
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)