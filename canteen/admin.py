from django.contrib import admin
from django.conf import settings
from django.db.models import Count
from django.utils.html import format_html

from .models import FoodItem, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = (
        'food_item',
        'food_name',
        'price',
        'quantity',
        'total_price',
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'customer_name',
        'customer_email',
        'item_count',
        'total_amount',
        'payment_method',
        'status_badge',
        'created_at',
    )
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = (
        'customer_name',
        'customer_email',
        '=id',
        'razorpay_order_id',
        'razorpay_payment_id',
    )
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    list_per_page = 25
    autocomplete_fields = ('user',)
    readonly_fields = (
        'status',
        'created_at',
        'stock_reserved',
        'razorpay_order_id',
        'razorpay_payment_id',
    )
    inlines = (OrderItemInline,)
    actions = (
        'mark_preparing',
        'mark_ready',
        'mark_completed',
        'cancel_orders',
    )

    @admin.display(description='Items', ordering='_item_count')
    def item_count(self, obj):
        return obj._item_count

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        return format_html(
            '<span class="status-badge status-{}">{}</span>',
            obj.status.lower(),
            obj.get_status_display(),
        )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_item_count=Count('items'))

    @admin.action(description='Mark selected orders as preparing')
    def mark_preparing(self, request, queryset):
        updated = queryset.filter(status='Pending').update(status='Preparing')
        self.message_user(request, f'{updated} order(s) marked as preparing.')

    @admin.action(description='Mark selected orders as ready')
    def mark_ready(self, request, queryset):
        updated = queryset.filter(status='Preparing').update(status='Ready')
        self.message_user(request, f'{updated} order(s) marked as ready.')

    @admin.action(description='Mark selected orders as completed')
    def mark_completed(self, request, queryset):
        updated = queryset.filter(status='Ready').update(status='Completed')
        self.message_user(request, f'{updated} order(s) marked as completed.')

    @admin.action(description='Cancel selected open orders and restore stock')
    def cancel_orders(self, request, queryset):
        cancelled = sum(order.cancel(allow_preparing=True) for order in queryset)
        self.message_user(
            request,
            f'{cancelled} order(s) cancelled and stock restored.',
        )


class LowStockFilter(admin.SimpleListFilter):
    title = 'stock level'
    parameter_name = 'stock_level'

    def lookups(self, request, model_admin):
        return (
            ('low', f'Low stock (≤ {settings.LOW_STOCK_THRESHOLD})'),
            ('healthy', f'Above {settings.LOW_STOCK_THRESHOLD}'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'low':
            return queryset.filter(stock__lte=settings.LOW_STOCK_THRESHOLD)
        if self.value() == 'healthy':
            return queryset.filter(stock__gt=settings.LOW_STOCK_THRESHOLD)
        return queryset

@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'image_preview',
        'price',
        'stock_alert',
        'is_available',
    )
    list_editable = ('price', 'is_available')
    list_filter = ('is_available', LowStockFilter)
    search_fields = ('name',)
    ordering = ('name',)
    list_per_page = 25
    readonly_fields = ('image_preview',)
    fieldsets = (
        ('Menu item', {
            'fields': ('name', 'price', 'stock', 'is_available'),
        }),
        ('Photo', {
            'fields': ('image', 'image_preview'),
        }),
    )

    @admin.display(description='Photo')
    def image_preview(self, obj):
        if not obj or not obj.image:
            return 'No image uploaded'
        return format_html(
            '<img src="{}" alt="{}" class="food-image-preview">',
            obj.image.url,
            obj.name,
        )

    @admin.display(description='Stock', ordering='stock')
    def stock_alert(self, obj):
        if obj.stock <= settings.LOW_STOCK_THRESHOLD:
            return format_html(
                '<strong style="color: #b42318;">Low stock: {}</strong>',
                obj.stock,
            )
        return obj.stock


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'food_name', 'price', 'quantity', 'total_price')
    list_filter = ('order__status', 'order__created_at')
    search_fields = ('food_name', 'order__customer_name', 'order__customer_email')
    date_hierarchy = 'order__created_at'
    ordering = ('-order__created_at',)
    list_per_page = 25
    readonly_fields = (
        'order',
        'food_item',
        'food_name',
        'price',
        'quantity',
        'total_price',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False