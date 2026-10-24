from django.core.management.base import BaseCommand

from canteen.models import FoodItem


FOOD_ITEMS = [
    ("chai", "10.00", 100),
    ("Coffee", "15.00", 100),
    ("Vegetable Sandwich", "40.00", 100),
    ("Aloo Butter Sandwich", "40.00", 100),
    ("Cheese and Jam Sandwich", "80.00", 100),
    ("Poha", "20.00", 100),
    ("Veg Pakoda", "25.00", 100),
    ("Kachori-Samosa", "30.00", 100),
    ("Vada Pav", "35.00", 100),
    ("Dabeli", "30.00", 100),
    ("Khaman Dhokla", "20.00", 100),
    ("Thepla", "20.00", 100),
    ("Aloo Paratha", "30.00", 100),
    ("Jalebi", "40.00", 100),
    ("Plain Dosa-Sambar", "60.00", 100),
    ("Masala Dosa-Sambar", "80.00", 100),
    ("Idli-Sambar (2 pcs)", "40.00", 100),
    ("Medu Vada-Sambar (2 pcs)", "50.00", 100),
    ("Puri-Sabji (4 pcs)", "40.00", 100),
    ("Lassi", "30.00", 50),
    ("Chhas", "20.00", 60),
    ("Fixed Thali", "70.00", 50),
    ("Unlimited Thali", "80.00", 50),
]


class Command(BaseCommand):
    help = "Create the initial canteen menu without changing existing items."

    def handle(self, *args, **options):
        created_count = 0
        for name, price, stock in FOOD_ITEMS:
            _, created = FoodItem.objects.get_or_create(
                name=name,
                defaults={
                    "price": price,
                    "stock": stock,
                    "is_available": True,
                },
            )
            created_count += created

        self.stdout.write(
            self.style.SUCCESS(f"Menu seed complete; added {created_count} food items.")
        )
