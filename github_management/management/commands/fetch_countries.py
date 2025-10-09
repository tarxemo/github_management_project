# management/commands/fetch_countries.py
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin
from github_management.models import Country

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetch and store all available countries from committers.top'

    def handle(self, *args, **options):
        base_url = "https://committers.top/"
        
        try:
            response = requests.get(base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all country links in the country list
            country_links = soup.select('ul.country-list a')
            countries = []
            
            for link in country_links:
                country_name = link.text.strip()
                slug = link['href'].strip('/')
                
                # Skip if already exists
                if Country.objects.filter(slug=slug).exists():
                    continue
                    
                countries.append(Country(
                    name=country_name,
                    slug=slug
                ))
                self.stdout.write(self.style.SUCCESS(f"Found country: {country_name}"))
            
            # Bulk create new countries
            if countries:
                Country.objects.bulk_create(countries)
                self.stdout.write(self.style.SUCCESS(f"Added {len(countries)} new countries"))
            else:
                self.stdout.write(self.style.SUCCESS("No new countries to add"))
                
        except Exception as e:
            logger.error(f"Error fetching countries: {e}", exc_info=True)
            self.stderr.write(self.style.ERROR(f"Error: {str(e)}"))