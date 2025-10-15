# users/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import User, UserFollowing
from django.contrib import messages
from .forms import *
from .services.github_service import GitHubService
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Exists, OuterRef, Case, When, Value, CharField

@login_required
def relationship_management(request):
    user = request.user
    
    # Get filter and search parameters
    filter_type = request.GET.get('filter', 'all')  # all, following, followers, mutual
    search_query = request.GET.get('search', '').strip()
    page_number = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 12)
    
    # Get all unique users in relationships with current user
    following_ids = UserFollowing.objects.filter(from_user=user).values_list('to_user_id', flat=True)
    follower_ids = UserFollowing.objects.filter(to_user=user).values_list('from_user_id', flat=True)
    
    # Combine all related user IDs
    all_related_ids = set(following_ids) | set(follower_ids)
    
    # Start with base queryset of all related users
    users_qs = User.objects.filter(id__in=all_related_ids).select_related()
    
    # Annotate each user with their relationship status
    users_qs = users_qs.annotate(
        is_following=Exists(
            UserFollowing.objects.filter(
                from_user=user,
                to_user=OuterRef('pk')
            )
        ),
        is_follower=Exists(
            UserFollowing.objects.filter(
                from_user=OuterRef('pk'),
                to_user=user
            )
        )
    ).annotate(
        relationship_status=Case(
            When(is_following=True, is_follower=True, then=Value('mutual')),
            When(is_following=True, is_follower=False, then=Value('following')),
            When(is_following=False, is_follower=True, then=Value('follower')),
            default=Value('none'),
            output_field=CharField()
        )
    )
    
    # Apply filters
    if filter_type == 'following':
        users_qs = users_qs.filter(is_following=True)
    elif filter_type == 'followers':
        users_qs = users_qs.filter(is_follower=True)
    elif filter_type == 'mutual':
        users_qs = users_qs.filter(is_following=True, is_follower=True)
    
    # Apply search filter
    if search_query:
        users_qs = users_qs.filter(
            Q(github_username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Order by most recent relationship
    users_qs = users_qs.order_by('-id')
    
    # Calculate stats
    stats = {
        'following': len([uid for uid in following_ids]),
        'followers': len([uid for uid in follower_ids]),
        'mutual': len(set(following_ids) & set(follower_ids)),
        'total': len(all_related_ids)
    }
    
    # Pagination
    try:
        per_page = int(per_page)
        if per_page not in [12, 24, 48]:
            per_page = 12
    except (ValueError, TypeError):
        per_page = 12
    
    paginator = Paginator(users_qs, per_page)
    
    try:
        users_page = paginator.page(page_number)
    except PageNotAnInteger:
        users_page = paginator.page(1)
    except EmptyPage:
        users_page = paginator.page(paginator.num_pages)
    User.with_fresh_data(users_page)
    context = {
        'users': users_page,
        'stats': stats,
        'filter_type': filter_type,
        'search_query': search_query,
        'per_page': per_page,
        'paginator': paginator,
    }
    
    return render(request, 'users/relationship_management.html', context)

@login_required
def relationship_stats(request):
    """API endpoint to get current relationship statistics"""
    user = request.user
    
    following_ids = list(UserFollowing.objects.filter(from_user=user).values_list('to_user_id', flat=True))
    follower_ids = list(UserFollowing.objects.filter(to_user=user).values_list('from_user_id', flat=True))
    
    stats = {
        'following': len(following_ids),
        'followers': len(follower_ids),
        'mutual': len(set(following_ids) & set(follower_ids)),
        'total': len(set(following_ids) | set(follower_ids))
    }
    
    return JsonResponse(stats)

@login_required
def follow_user(request, username):
    target_user = get_object_or_404(User, github_username__iexact=username)
    GitHubService.follow_user_on_github(request.user, target_user.github_username)
    return redirect('relationship_management')

@login_required
def unfollow_user(request, username):
    target_user = get_object_or_404(User, github_username__iexact=username)
    GitHubService.unfollow_user_on_github(request.user, target_user.github_username)
    return redirect('relationship_management')

@login_required
def relationship_stats(request):
    user = request.user
    
    return JsonResponse({
        'following': UserFollowing.objects.filter(from_user=user).count(),
        'followers': UserFollowing.objects.filter(to_user=user).count(),
        'mutual': UserFollowing.objects.filter(
            Q(from_user=user) & Q(to_user__in=follower_users)
        ).count()
    })


@login_required
def add_github_token(request):
    if request.method == 'POST':
        form = GitHubTokenForm(request.POST)
        if form.is_valid():
            request.user.github_access_token = form.cleaned_data['access_token']
            request.user.save()
            messages.success(request, 'GitHub token saved successfully!')
            return redirect('profile')  # Or wherever you want to redirect
    else:
        form = GitHubTokenForm()
    
    return render(request, 'users/add_github_token.html', {'form': form})