from django import forms
from django.contrib.auth import get_user_model
from allauth.account.forms import SignupForm as AllAuthSignupForm
from django.core.validators import RegexValidator

User = get_user_model()

class CustomSignupForm(AllAuthSignupForm):
    """Custom signup form that doesn't require or use a username."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the username field if it exists
        if 'username' in self.fields:
            del self.fields['username']
    
    def save(self, request):
        # Ensure we don't try to save a username
        user = super().save(request)
        return user

class GitHubTokenForm(forms.Form):
    access_token = forms.CharField(
        label='GitHub Access Token',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your GitHub access token'
        }),
        validators=[
            RegexValidator(
                regex='^[A-Za-z0-9_]*$',
                message='Please enter a valid GitHub access token',
                code='invalid_token'
            )
        ]
    )