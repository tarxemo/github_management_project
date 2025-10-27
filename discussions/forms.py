from django import forms
from .models import Thread, Post


class ThreadForm(forms.ModelForm):
    class Meta:
        model = Thread
        fields = ['title', 'body_md']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Thread title'}),
            'body_md': forms.Textarea(attrs={'rows': 10, 'class': 'textarea', 'placeholder': 'Write in Markdown...'}),
        }


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['body_md']
        widgets = {
            'body_md': forms.Textarea(attrs={'rows': 6, 'class': 'textarea', 'placeholder': 'Reply in Markdown...'}),
        }
