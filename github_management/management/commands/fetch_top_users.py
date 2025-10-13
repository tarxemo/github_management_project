import os
import time
import logging
import json
from typing import List, Dict, Optional
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction

from github_management.models import GitHubUser
from github_management.services.github_api import GitHubAPIClient

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetch and store top GitHub users by contributions for specified countries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--countries',
            type=str,
            help='Comma-separated list of countries to fetch users for',
            default='United States,China,India,United Kingdom,Germany,Japan,Brazil,Russia,France,Canada'
        )
        parser.add_argument(
            '--max-users-per-country',
            type=int,
            default=250,
            help='Maximum number of users to fetch per country (default: 250)'
        )
        parser.add_argument(
            '--pages-per-country',
            type=int,
            default=250,
            help='Maximum number of pages to fetch per country (default: 10, 100 users per page)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without saving to database'
        )

    def handle(self, *args, **options):
        # Get GitHub token from environment or settings
        github_token = os.getenv('GITHUB_TOKEN')
        if not github_token:
            github_token = getattr(settings, 'GITHUB_TOKEN', None)
            
        if not github_token:
            raise CommandError('GitHub token not found. Please set GITHUB_TOKEN environment variable or in settings.py')

        # Parse countries
        countries = [c.strip() for c in options['countries'].split(',') if c.strip()]
        if not countries:
            raise CommandError('No valid countries provided')

        # Initialize GitHub API client
        github_client = GitHubAPIClient(github_token)
        
        # Process each country
        for country in countries:
            self.stdout.write(self.style.SUCCESS(f'Processing country: {country}'))
            try:
                self.process_country(
                    github_client=github_client,
                    country=country,
                    max_users=options['max_users_per_country'],
                    max_pages=options['pages_per_country'],
                    dry_run=options['dry_run']
                )
            except Exception as e:
                logger.error(f"Error processing country {country}: {e}", exc_info=True)
                self.stderr.write(self.style.ERROR(f'Error processing {country}: {str(e)}'))
                continue

    def process_country(
        self,
        github_client: GitHubAPIClient,
        country: str,
        max_users: int = 200,
        max_pages: int = 10,
        dry_run: bool = False
    ) -> None:
        """Process a single country to fetch and store top users by contributions."""
        self.stdout.write(f"Fetching top {max_users} active users from {country}...")
        
        try:
            # Get users from committers.top
            users = github_client.get_users_by_country(country.lower(), max_users=max_users)
            
            if not users:
                self.stdout.write(self.style.WARNING(f"No users found for {country}"))
                return
                
            # Convert to the format expected by our model
            all_users = []
            for user in users:
                # Split name into first and last name if available
                name = user.get('name', '').strip()
                first_name = ''
                last_name = ''
                if name:
                    name_parts = name.split(' ', 1)
                    first_name = name_parts[0]
                    last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                user_data = {
                    'username': user['username'],
                    'first_name': first_name,
                    'last_name': last_name,
                    'followers': user.get('followers', 0),
                    'following': 0,  # Not available from committers.top
                    'contributions_last_year': user.get('contributions', 0),
                    'country': country,
                    'profile_url': user.get('profile_url', f"https://github.com/{user['username']}"),
                    'avatar_url': user.get('avatar_url', f"https://github.com/{user['username']}.png")
                }
                all_users.append(user_data)
            
            # Sort users by contributions (descending)
            all_users.sort(key=lambda x: x['contributions_last_year'], reverse=True)
            
            # Truncate to max_users
            all_users = all_users[:max_users]
            
            self.stdout.write(f"\nTop {len(all_users)} users in {country} by contributions:")
            for i, user in enumerate(all_users[:10], 1):
                self.stdout.write(f"  {i:2d}. {user['username']}: {user['contributions_last_year']} contributions")
            
            if len(all_users) > 10:
                self.stdout.write(f"  ... and {len(all_users) - 10} more")
            
            if dry_run:
                self.stdout.write("\nDry run - not saving to database")
                return
            
            # Save to database in a transaction
            with transaction.atomic():
                # Delete existing users for this country
                deleted_count, _ = GitHubUser.objects.filter(country=country).delete()
                self.stdout.write(f"Deleted {deleted_count} existing records for {country}")
                
                # Create new records
                users_to_create = [
                    GitHubUser(**user_data)
                    for user_data in all_users
                ]
                
                created_count = len(GitHubUser.objects.bulk_create(users_to_create))
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully saved {created_count} users for {country}"
                ))
                
                # Update fetched_at timestamp for all users of this country
                GitHubUser.objects.filter(country=country).update(fetched_at=datetime.now())
            
            # Add a small delay between countries
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"Error processing country {country}: {e}", exc_info=True)
            self.stderr.write(self.style.ERROR(f'Error processing {country}: {str(e)}'))
