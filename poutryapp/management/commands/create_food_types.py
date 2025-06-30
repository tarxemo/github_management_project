from django.core.management.base import BaseCommand
from poutryapp.models import FoodType 

class Command(BaseCommand):
    help = 'Create default food types: starter, grower, and complete'

    def handle(self, *args, **kwargs):
        food_types = [
            {"name": "starter", "description": "For newly hatched chicks"},
            {"name": "grower", "description": "For growing chickens"},
            {"name": "complete", "description": "For adult chickens, complete diet"}
        ]

        for food in food_types:
            obj, created = FoodType.objects.get_or_create(name=food["name"], defaults={"description": food["description"]})
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created food type: {obj.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Food type already exists: {obj.name}'))
