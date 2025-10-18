from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.conf import settings
from django.core.paginator import Paginator
from .models import Country, GitHubUser

# Get the current site domain
def get_base_url():
    return getattr(settings, 'SITE_URL', 'https://github.tarxemo.com')

base_url = get_base_url()

class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'daily'
    items_per_page = 20  # Match the pagination in CountryListView

    def items(self):
        # Base static pages
        base_items = ['home', 'follow_random', 'unfollow_non_followers']
        
        # Add paginated country list pages
        country_count = Country.objects.count()
        num_pages = (country_count + self.items_per_page - 1) // self.items_per_page
        country_pages = [f'country_list_page_{i+1}' for i in range(num_pages)]
        
        return base_items + country_pages

    def location(self, item):
        if item.startswith('country_list_page_'):
            page = item.split('_')[-1]
            return f"{reverse('github_management:country_list')}?page={page}"
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
    items_per_page = 25  # Match the pagination in CountryDetailView

    def items(self):
        items = []
        countries = Country.objects.all()
        
        for country in countries:
            # Add the base country detail URL
            items.append((country.slug, 0))
            
            # Add paginated versions
            user_count = country.users.count()
            num_pages = (user_count + self.items_per_page - 1) // self.items_per_page
            for page in range(1, num_pages + 1):
                items.append((country.slug, page))
                
        return items

    def lastmod(self, obj):
        country_slug, _ = obj
        country = Country.objects.get(slug=country_slug)
        return country.last_updated or None

    def location(self, obj):
        country_slug, page = obj
        base_url = reverse('github_management:country_detail', kwargs={'slug': country_slug})
        if page > 0:
            return f"{base_url}?page={page}"
        return base_url

    def get_urls(self, **kwargs):
        urls = []
        for item in self.items():
            country_slug, page = item
            country = Country.objects.get(slug=country_slug)
            
            urls.append({
                'location': f"{base_url}{self.location(item)}",
                'lastmod': country.last_updated,
                'changefreq': self.changefreq,
                'priority': self.priority if page <= 1 else max(0.1, self.priority - 0.2),  # Lower priority for paginated pages
            })
        return urls

class UserSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return GitHubUser.objects.all()

    def location(self, obj):
        return reverse('github_management:user_detail', kwargs={'github_username': obj.github_username})

    def lastmod(self, obj):
        return obj.fetched_at or None

    def get_urls(self, **kwargs):
        return [{
            'location': f"{base_url}{self._location(item)}",
            'lastmod': self.lastmod(item),
            'changefreq': self.changefreq,
            'priority': self.priority,
        } for item in self.items()]

# Sitemap index
class SitemapIndex(Sitemap):
    def items(self):
        return [
            ('static', StaticViewSitemap),
            ('countries', CountrySitemap),
            ('users', UserSitemap),
        ]

    def location(self, item):
        return reverse('django.contrib.sitemaps.views.sitemap', kwargs={'section': item[0]})

sitemaps = {
    'static': StaticViewSitemap,
    'countries': CountrySitemap,
    'users': UserSitemap,
}