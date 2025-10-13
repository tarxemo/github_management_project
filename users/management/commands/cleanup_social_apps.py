from django.core.management.base import BaseCommand
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

class Command(BaseCommand):
    help = 'Clean up duplicate social apps and ensure proper site associations'

    def handle(self, *args, **options):
        # Get current site
        site = Site.objects.get_current()
        self.stdout.write(f"Current site: {site.domain} (ID: {site.id})")
        
        # Process each provider type
        for provider in ['google', 'github']:
            self.stdout.write(f"\nProcessing {provider} apps...")
            apps = SocialApp.objects.filter(provider=provider)
            
            if not apps.exists():
                self.stdout.write(f"No {provider} apps found.")
                continue
                
            if apps.count() == 1:
                app = apps.first()
                if site not in app.sites.all():
                    app.sites.add(site)
                    app.save()
                    self.stdout.write(f"Added site to existing {provider} app: {app.name}")
                else:
                    self.stdout.write(f"Single {provider} app is properly configured.")
                continue
                
            # If we have multiple apps, keep the first one
            self.stdout.write(f"Found {apps.count()} {provider} apps. Cleaning up...")
            
            # Keep the first app and update its sites
            first_app = apps.first()
            if site not in first_app.sites.all():
                first_app.sites.add(site)
                first_app.save()
                self.stdout.write(f"Updated sites for primary {provider} app: {first_app.name}")
            
            # Delete all other apps
            deleted_count, _ = apps.exclude(pk=first_app.pk).delete()
            self.stdout.write(f"Removed {deleted_count} duplicate {provider} app(s).")
        
        self.stdout.write("\nCleanup complete!")
