from typing import Dict, Any
from django.shortcuts import get_object_or_404
from github_management.models import GitHubUser, Country


def _impact_score(user: GitHubUser) -> int:
    followers = user.followers or 0
    repos = user.public_repos or 0
    contrib = user.contributions_last_year or 0
    gists = user.public_gists or 0
    # Weighted creative score
    score = int(0.5 * followers + 0.2 * repos + 0.25 * contrib / 10 + 0.05 * gists)
    return max(score, 0)


def _streak_info(user: GitHubUser) -> Dict[str, Any]:
    # Placeholder: in absence of per-day data, approximate from contributions_last_year
    days = min(100, (user.contributions_last_year or 0) // 3)
    best = max(days, 10)
    return {"current": days, "best": best}


def get_badge_context(username: str, badge_type: str, animated: bool, request=None) -> Dict[str, Any]:
    user = get_object_or_404(GitHubUser, github_username__iexact=username)

    base = {
        'username': user.github_username,
        'display_name': user.display_name or user.github_username,
        'avatar_url': user.avatar_url,
        'profile_url': user.profile_url,
        'animated': animated,
        'country': getattr(user.country, 'name', None),
        'country_slug': getattr(user.country, 'slug', None),
    }

    if badge_type == 'stats':
        base.update({
            'followers': user.followers,
            'following': user.following,
            'public_repos': user.public_repos,
            'contributions_last_year': user.contributions_last_year,
            'rank': user.rank,
        })
    elif badge_type == 'rank':
        # global = user.rank; country position derived from country users
        country_rank = None
        if user.country_id:
            country_rank = GitHubUser.objects.filter(country_id=user.country_id, rank__lte=user.rank).count()
        base.update({'global_rank': user.rank, 'country_rank': country_rank})
    elif badge_type == 'streak':
        base.update({'streak': _streak_info(user)})
    elif badge_type == 'impact':
        base.update({'impact': _impact_score(user)})
    elif badge_type == 'langs':
        # Placeholder: if language stats exist elsewhere, wire here. Provide empty for now.
        base.update({'languages': []})
    elif badge_type == 'country-top':
        # Compute percentile in country
        percentile = None
        if user.country_id:
            total = GitHubUser.objects.filter(country_id=user.country_id).count() or 1
            percentile = round((user.rank / total) * 100, 1)
        base.update({'country_percentile': percentile})
    else:
        raise ValueError('Unknown badge type')

    return base
