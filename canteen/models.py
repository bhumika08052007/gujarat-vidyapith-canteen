
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import transaction
from django.db.models import F, Q


class FoodItem(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    stock = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    image = models.ImageField(
        upload_to='food_images/',
        blank=True,
        null=True
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(price__gte=0),
                name='food_item_price_nonnegative',
            ),
            models.CheckConstraint(
                condition=Q(stock__gte=0),
                name='food_item_stock_nonnegative',
            ),
        ]

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Preparing', 'Preparing'),
        ('Ready', 'Ready'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    payment_method = models.CharField(max_length=50)
    total_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    stock_reserved = models.BooleanField(default=False, editable=False)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(total_amount__gte=0),
                name='order_total_nonnegative',
            ),
        ]

    def __str__(self):
        return f"Order #{self.id} - {self.customer_name} (₹{self.total_amount})"

    def cancel(self, allow_preparing=False):
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=self.pk)
            cancellable_statuses = ('Pending', 'Preparing', 'Ready')
            if order.status not in cancellable_statuses:
                return False
            if not allow_preparing and order.status != 'Pending':
                return False

            if order.stock_reserved:
                for item in order.items.select_related('food_item'):
                    if item.food_item_id:
                        FoodItem.objects.filter(pk=item.food_item_id).update(
                            stock=F('stock') + item.quantity
                        )
                order.stock_reserved = False

            order.status = 'Cancelled'
            order.save(update_fields=('status', 'stock_reserved'))
            self.status = order.status
            return True


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    food_item = models.ForeignKey(
        FoodItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    food_name = models.CharField(max_length=100)
    price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    total_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(price__gte=0),
                name='order_item_price_nonnegative',
            ),
            models.CheckConstraint(
                condition=Q(quantity__gte=1),
                name='order_item_quantity_positive',
            ),
            models.CheckConstraint(
                condition=Q(total_price__gte=0),
                name='order_item_total_nonnegative',
            ),
        ]

    def __str__(self):
        return f"{self.food_name} x {self.quantity}"
