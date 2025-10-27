from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.contrib import messages

from .models import Topic, Thread, Post
from .forms import ThreadForm, PostForm


class TopicListView(ListView):
    model = Topic
    template_name = 'discussions/topic_list.html'
    context_object_name = 'topics'


class TopicDetailView(ListView):
    model = Thread
    template_name = 'discussions/topic_detail.html'
    context_object_name = 'threads'
    paginate_by = 20

    def get_queryset(self):
        self.topic = get_object_or_404(Topic, slug=self.kwargs['slug'])
        return Thread.objects.filter(topic=self.topic)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['topic'] = self.topic
        return ctx


class ThreadCreateView(LoginRequiredMixin, CreateView):
    model = Thread
    form_class = ThreadForm
    template_name = 'discussions/thread_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.topic = get_object_or_404(Topic, slug=kwargs.get('slug'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['topic'] = self.topic
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.topic = self.topic
        obj.author = self.request.user
        obj.save()
        messages.success(self.request, 'Thread created successfully!')
        return redirect(obj.get_absolute_url())


class ThreadDetailView(DetailView):
    model = Thread
    template_name = 'discussions/thread_detail.html'
    context_object_name = 'thread'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        posts = self.object.posts.all()
        paginator = Paginator(posts, 20)
        page_number = self.request.GET.get('page')
        ctx['page_obj'] = paginator.get_page(page_number)
        ctx['post_form'] = PostForm() if self.request.user.is_authenticated else None
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.user.is_authenticated:
            messages.error(request, 'Login required to reply.')
            return redirect('account_login')
        if self.object.is_locked:
            messages.error(request, 'Thread is locked.')
            return redirect(self.object.get_absolute_url())
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.thread = self.object
            post.author = request.user
            post.save()
            messages.success(request, 'Reply posted!')
            return redirect(self.object.get_absolute_url())
        ctx = self.get_context_data()
        ctx['post_form'] = form
        return render(request, self.template_name, ctx)
