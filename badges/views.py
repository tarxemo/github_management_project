from django.http import HttpResponse, Http404
from django.views.decorators.http import require_GET
from django.views.decorators.cache import cache_page
from django.utils.cache import patch_response_headers
from django.template.loader import render_to_string
from django.utils.module_loading import import_string
from django.conf import settings

from .services.badge_data import get_badge_context
from .utils.svg_renderer import render_svg_with_theme, try_render_png

CACHE_TIMEOUT = 60 * 60  # 1 hour


@require_GET
@cache_page(CACHE_TIMEOUT)
def github_badge(request, username: str, badge_type: str):
    theme = request.GET.get('theme', 'cyberpunk')
    animated = request.GET.get('animated', 'true').lower() in ('1', 'true', 'yes', 'on')
    fmt = request.GET.get('format', 'svg').lower()
    text_color = request.GET.get('text', None)

    try:
        context = get_badge_context(username=username, badge_type=badge_type, animated=animated, request=request)
    except Http404:
        raise
    except Exception:
        raise Http404('Badge data not available')

    template_map = {
        'stats': 'badges/stats_badge.svg',
        'rank': 'badges/rank_badge.svg',
        'streak': 'badges/streak_badge.svg',
        'langs': 'badges/langs_badge.svg',
        'impact': 'badges/impact_badge.svg',
        'country-top': 'badges/country_top_badge.svg',
        'trophies': 'badges/trophies_badge.svg',
    }
    template_name = template_map.get(badge_type)
    if not template_name:
        raise Http404('Unknown badge type')

    svg = render_svg_with_theme(template_name, context={**context, 'theme_name': theme, 'animated': animated, 'text_override': text_color})

    if fmt == 'png':
        png_bytes = try_render_png(svg)
        if png_bytes is not None:
            resp = HttpResponse(png_bytes, content_type='image/png')
            patch_response_headers(resp, cache_timeout=CACHE_TIMEOUT)
            return resp
        # fallback to SVG if PNG renderer unavailable

    resp = HttpResponse(svg, content_type='image/svg+xml')
    patch_response_headers(resp, cache_timeout=CACHE_TIMEOUT)
    return resp

from django.views.generic import ListView
from .models import Achievement, UserAchievement

class AchievementListView(ListView):
    model = Achievement
    template_name = 'github_management/achievements.html'
    context_object_name = 'all_achievements'

    def get_queryset(self):
        return Achievement.objects.all().order_by('tier', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            user_achievements = UserAchievement.objects.filter(user=self.request.user)
            unlocked_map = {ua.achievement_id: ua for ua in user_achievements}
            
            # Enrich achievement objects with user status
            for achievement in context['all_achievements']:
                ua = unlocked_map.get(achievement.id)
                achievement.is_unlocked = ua.is_unlocked if ua else False
                achievement.unlocked_at = ua.unlocked_at if ua else None
                achievement.progress = ua.progress_json if ua else 0 # Simple mock progress
        return context
