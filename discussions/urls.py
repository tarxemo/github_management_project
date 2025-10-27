from django.urls import path
from .views import TopicListView, TopicDetailView, ThreadDetailView, ThreadCreateView

app_name = 'discussions'

urlpatterns = [
    path('', TopicListView.as_view(), name='topic_list'),
    path('t/<slug:slug>/', TopicDetailView.as_view(), name='topic_detail'),
    path('t/<slug:slug>/new/', ThreadCreateView.as_view(), name='thread_create'),
    path('thread/<slug:slug>/', ThreadDetailView.as_view(), name='thread_detail'),
]
