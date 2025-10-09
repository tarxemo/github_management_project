from django import forms
from django.contrib.auth import get_user_model
from allauth.account.forms import SignupForm as AllAuthSignupForm

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
