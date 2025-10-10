from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

class CountryListView(LoginRequiredMixin, ListView):
    template_name = 'github_management/country_list.html'
    context_object_name = 'countries'
    paginate_by = 20

    def get_queryset(self):
        from django_countries import countries
        
        # Get search query if any
        search_query = self.request.GET.get('q', '').strip()
        
        # Convert countries to a list of dictionaries for easier manipulation
        country_list = [
            {'code': code, 'name': name}
            for code, name in sorted(countries)
        ]
        
        # Apply search filter
        if search_query:
            country_list = [
                country for country in country_list 
                if search_query.lower() in country['name'].lower()
            ]
            
        return country_list
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context
