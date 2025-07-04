from django.core.management.base import BaseCommand
from decimal import Decimal
from poutryapp.models import ChickenHouse

class Command(BaseCommand):
    help = "Update age of chickens in all chicken houses"

    def handle(self, *args, **kwargs):
        houses = ChickenHouse.objects.all_objects()
        for house in houses:
            house.age_in_weeks += Decimal("0.142857")  # 1 day = 1/7 week
            house.save()
        self.stdout.write(self.style.SUCCESS("Successfully updated chicken ages."))
