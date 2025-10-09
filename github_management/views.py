# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.core.paginator import Paginator
from .models import Country, GitHubUser
from .services.github_api import GitHubAPIClient
import logging

logger = logging.getLogger(__name__)

class CountryListView(View):
    """View to list all available countries"""
    def get(self, request):
        countries = Country.objects.all().order_by('name')
        return render(request, 'github_management/country_list.html', {
            'countries': countries,
            'active_tab': 'countries'
        })

class CountryDetailView(View):
    """View to show users for a specific country"""
    def get(self, request, slug):
        country = get_object_or_404(Country, slug=slug)
        users = country.users.all().order_by('rank')
        
        # Pagination
        paginator = Paginator(users, 25)  # Show 25 users per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'github_management/country_detail.html', {
            'country': country,
            'page_obj': page_obj,
            'active_tab': 'countries'
        })

class FetchUsersView(View):
    """View to trigger user fetching for a country"""
    def post(self, request, slug):
        country = get_object_or_404(Country, slug=slug)
        
        if country.is_fetching:
            messages.warning(request, f"Users for {country.name} are already being fetched. Please wait.")
            return redirect('github_management:country_detail', slug=slug)
            
        # Mark as fetching
        country.is_fetching = True
        country.save()
        
        try:
            # Import here to avoid circular imports
            from .tasks import fetch_users_for_country
            fetch_users_for_country.delay(country.id)
            messages.success(request, f"Started fetching users for {country.name}. This may take a while...")
        except Exception as e:
            logger.error(f"Error starting user fetch for {country.name}: {e}")
            country.is_fetching = False
            country.save()
            messages.error(request, f"Failed to start fetching users: {str(e)}")
            
        return redirect('github_management:country_detail', slug=slug)

class FetchStatusView(View):
    """API endpoint to check fetch status"""
    def get(self, request, slug):
        country = get_object_or_404(Country, slug=slug)
        return JsonResponse({
            'is_fetching': country.is_fetching,
            'last_updated': country.last_updated.isoformat() if country.last_updated else None,
            'user_count': country.user_count
        })