from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Verify and fix social app configuration'

    def handle(self, *args, **options):
        # Get or create the default site
        site = Site.objects.get_or_create(
            id=1,
            defaults={
                'domain': os.getenv('SITE_URL', 'github.tarxemo.com'),
                'name': 'GitHub Management'
            }
        )[0]
        
        # Update site domain if it's different
        if site.domain != os.getenv('SITE_URL', 'github.tarxemo.com'):
            site.domain = os.getenv('SITE_URL', 'github.tarxemo.com')
            site.save()
            self.stdout.write(self.style.SUCCESS(f'Updated site domain to: {site.domain}'))
        
        # Google OAuth2
        google_client_id = os.getenv('GOOGLE_OAUTH2_CLIENT_ID')
        google_secret = os.getenv('GOOGLE_OAUTH2_SECRET')
        
        if google_client_id and google_secret:
            google_app, created = SocialApp.objects.get_or_create(
                provider='google',
                defaults={
                    'name': 'Google',
                    'client_id': google_client_id,
                    'secret': google_secret
                }
            )
            
            # Update credentials if they've changed
            if not created and (google_app.client_id != google_client_id or google_app.secret != google_secret):
                google_app.client_id = google_client_id
                google_app.secret = google_secret
                google_app.save()
                self.stdout.write(self.style.SUCCESS('Updated Google OAuth2 credentials'))
            
            # Ensure site is associated
            if site not in google_app.sites.all():
                google_app.sites.add(site)
                self.stdout.write(self.style.SUCCESS('Added site to Google OAuth2 app'))
            
            self.stdout.write(self.style.SUCCESS('Google OAuth2 is properly configured'))
        else:
            self.stdout.write(self.style.WARNING('Google OAuth2 credentials not found in environment variables'))
        
        # GitHub OAuth2
        github_client_id = os.getenv('GITHUB_OAUTH2_CLIENT_ID')
        github_secret = os.getenv('GITHUB_OAUTH2_SECRET')
        
        if github_client_id and github_secret:
            github_app, created = SocialApp.objects.get_or_create(
                provider='github',
                defaults={
                    'name': 'GitHub',
                    'client_id': github_client_id,
                    'secret': github_secret
                }
            )
            
            # Update credentials if they've changed
            if not created and (github_app.client_id != github_client_id or github_app.secret != github_secret):
                github_app.client_id = github_client_id
                github_app.secret = github_secret
                github_app.save()
                self.stdout.write(self.style.SUCCESS('Updated GitHub OAuth2 credentials'))
            
            # Ensure site is associated
            if site not in github_app.sites.all():
                github_app.sites.add(site)
                self.stdout.write(self.style.SUCCESS('Added site to GitHub OAuth2 app'))
            
            self.stdout.write(self.style.SUCCESS('GitHub OAuth2 is properly configured'))
        else:
            self.stdout.write(self.style.WARNING('GitHub OAuth2 credentials not found in environment variables'))
        
        # List all social apps
        self.stdout.write(self.style.SUCCESS('\nCurrent social apps:'))
        for app in SocialApp.objects.all():
            self.stdout.write(f"- {app.name} ({app.provider}): {app.client_id}")
            self.stdout.write(f"  Sites: {', '.join([s.domain for s in app.sites.all()])}")
            
        self.stdout.write(self.style.SUCCESS('\nRun `python manage.py migrate` if you see any pending migrations.'))
