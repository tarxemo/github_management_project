from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.conf import settings
from django.core.paginator import Paginator
from .models import Country, GitHubUser

# Get the current site domain
def get_base_url():
    return 'https://github.tarxemo.com'

base_url = get_base_url()

class OtherUrlsSitemap(Sitemap):
    """Combined sitemap for static pages and country list/detail pages."""
    changefreq = 'daily'
    priority = 0.8
    list_items_per_page = 20   # Match the pagination in CountryListView
    detail_items_per_page = 25 # Match the pagination in CountryDetailView

    def items(self):
        items = []

        # Base static pages
        base_items = ['home', 'follow_random', 'unfollow_non_followers']
        for name in base_items:
            items.append(('static', name))

        # Paginated country list pages
        country_count = Country.objects.count()
        num_pages = (country_count + self.list_items_per_page - 1) // self.list_items_per_page
        for page in range(1, num_pages + 1):
            items.append(('country_list', page))

        # Country detail + paginated user list per country
        countries = Country.objects.all()
        for country in countries:
            # Base country detail URL
            items.append(('country_detail', country.slug, 0))

            # Paginated versions
            user_count = country.users.count()
            num_pages = (user_count + self.detail_items_per_page - 1) // self.detail_items_per_page
            for page in range(1, num_pages + 1):
                items.append(('country_detail', country.slug, page))

        return items

    def lastmod(self, obj):
        kind = obj[0]
        if kind == 'country_detail':
            _, country_slug, _ = obj
            country = Country.objects.get(slug=country_slug)
            return country.last_updated or None
        return None

    def location(self, obj):
        kind = obj[0]
        if kind == 'static':
            _, name = obj
            return reverse(f'github_management:{name}')
        if kind == 'country_list':
            _, page = obj
            return f"{reverse('github_management:country_list')}?page={page}"
        if kind == 'country_detail':
            _, country_slug, page = obj
            base_url = reverse('github_management:country_detail', kwargs={'slug': country_slug})
            if page > 0:
                return f"{base_url}?page={page}"
            return base_url
        # Fallback (should not normally be hit)
        return '/' 

class UserSitemapPart1(Sitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return GitHubUser.objects.order_by('id')[:25000]

    def location(self, obj):
        return reverse('github_management:user_detail', kwargs={'github_username': obj.github_username})

    def lastmod(self, obj):
        return obj.fetched_at or None

class UserSitemapPart2(Sitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return GitHubUser.objects.order_by('id')[25000:]

    def location(self, obj):
        return reverse('github_management:user_detail', kwargs={'github_username': obj.github_username})

    def lastmod(self, obj):
        return obj.fetched_at or None

# Sitemap index
class SitemapIndex(Sitemap):
    def items(self):
        # Exactly three sitemap sections:
        #  - users-1: first 25,000 GitHub users
        #  - users-2: remaining GitHub users
        #  - other:   all remaining URLs (static pages and country pages)
        return [
            ('users-1', UserSitemapPart1),
            ('users-2', UserSitemapPart2),
            ('other', OtherUrlsSitemap),
        ]

    def location(self, item):
        return reverse('django.contrib.sitemaps.views.sitemap', kwargs={'section': item[0]})

sitemaps = {
   'users-1': UserSitemapPart1,
   'users-2': UserSitemapPart2,
   'other': OtherUrlsSitemap,
}