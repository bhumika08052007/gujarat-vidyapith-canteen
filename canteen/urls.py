from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("menu/", views.menu, name="menu"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:item_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("payment/", views.payment, name="payment"),
    path("payment/gpay/", views.gpay_payment, name="gpay_payment"),
    path("payment-success/", views.payment_success, name="payment_success"),
    path("order-success/", views.order_success, name="order_success"),
    path("orders/", views.order_history, name="order_history"),
    path("orders/status/", views.order_status_updates, name="order_status_updates"),
    path("orders/<int:order_id>/cancel/", views.cancel_order, name="cancel_order"),
    path("orders/<int:order_id>/cancel/", views.cancel_order, name="cancel_order"),
]
