from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.contrib.sites.models import Site
from django.conf import settings
from .models import Country, GitHubUser

# Get the current site domain
try:
    current_site = Site.objects.get_current()
    base_url = f'https://{current_site.domain}'
except:
    base_url = 'https://github.tarxemo.com'  # Fallback URL

class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'daily'

    def items(self):
        return ['home', 'country_list', 'follow_random', 'unfollow_non_followers']

    def location(self, item):
        return reverse(f'github_management:{item}')

    def get_urls(self, **kwargs):
        return [{
            'location': f"{base_url}{self._location(item)}",
            'lastmod': None,
            'changefreq': self.changefreq,
            'priority': self.priority,
        } for item in self.items()]

class CountrySitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.9

    def items(self):
        return Country.objects.all()

    def lastmod(self, obj):
        return obj.last_updated or None

    def location(self, obj):
        return reverse('github_management:country_detail', kwargs={'slug': obj.slug})

    def get_urls(self, **kwargs):
        return [{
            'location': f"{base_url}{self._location(item)}",
            'lastmod': self.lastmod(item),
            'changefreq': self.changefreq,
            'priority': self.priority,
        } for item in self.items()]

class UserSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return GitHubUser.objects.all()

    def location(self, obj):
        return reverse('github_management:user_detail', kwargs={'username': obj.username})

    def get_urls(self, **kwargs):
        return [{
            'location': f"{base_url}{self._location(item)}",
            'lastmod': None,
            'changefreq': self.changefreq,
            'priority': self.priority,
        } for item in self.items()]

sitemaps = {
    'static': StaticViewSitemap,
    'countries': CountrySitemap,
    'users': UserSitemap,
}