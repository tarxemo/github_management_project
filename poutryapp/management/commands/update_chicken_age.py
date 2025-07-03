# yourapp/management/commands/update_chicken_age.py

from django.core.management.base import BaseCommand
from datetime import timedelta
from django.utils.timezone import now
from poutryapp.models import ChickenHouse

class Command(BaseCommand):
    help = "Update age of chickens in all chicken houses"

    def handle(self, *args, **kwargs):
        houses = ChickenHouse.objects.all_objects()
        for house in houses:
            house.age_in_weeks += 1/7
            house.save()
        self.stdout.write(self.style.SUCCESS("Successfully updated chicken ages."))
