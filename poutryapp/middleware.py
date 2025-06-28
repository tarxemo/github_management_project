# middleware.py
import jwt
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from .models import SystemLog
logger = logging.getLogger(__name__)
import jwt
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
import json
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

from datetime import datetime, time, date
from decimal import Decimal
from django.db.models.fields.files import FieldFile

def serialize_value(value):
    if isinstance(value, (datetime, time, date)):
        return value.isoformat()
    elif isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, FieldFile):  # Handles ImageFieldFile and FileField
        return value.url if value and hasattr(value, 'url') else None
    elif isinstance(value, (list, dict, str, int, float, bool, type(None))):
        return value  # Already serializable
    else:
        return str(value)  # Fallback



class AuditLogGraphQLMiddleware:
    def __init__(self, get_response=None):
        # This makes it work with both Django middleware and GraphQL middleware
        self.get_response = get_response
        # Connect signals
        post_save.connect(self.log_save, dispatch_uid='log_save_graphql')
        post_delete.connect(self.log_delete, dispatch_uid='log_delete_graphql')
        pre_save.connect(self.capture_pre_save_state, dispatch_uid='capture_pre_save_state')
        post_save.connect(self.log_save, dispatch_uid='log_save_graphql')
        post_delete.connect(self.log_delete, dispatch_uid='log_delete_graphql')
        
    def __call__(self, request):
        if self.get_response:
            self.request = request
            response = self.get_response(request)
            return response
        return self

    def capture_pre_save_state(self, sender, instance, **kwargs):
        """Capture the state of the instance before it is saved."""
        if sender == SystemLog:
            return

        previous_state = {}
        try:
            if instance.pk:  # Only if the object already exists (i.e., not being created)
                original = sender.objects.get(pk=instance.pk)
                for field in original._meta.fields:
                    value = getattr(original, field.name)
                    previous_state[field.name] = serialize_value(value)
                # Store it temporarily on the instance for later use in post_save
                instance._pre_save_state = previous_state
        except sender.DoesNotExist:
            instance._pre_save_state = None

    def resolve(self, next, root, info, **kwargs):
        self.request = info.context
        return next(root, info, **kwargs)

    def get_user(self):
        """Get the current user from the request (already set by JWTAuthenticationMiddleware)"""
        if hasattr(self, 'request') and hasattr(self.request, 'user'):
            return self.request.user if not self.request.user.is_anonymous else None
        return None

    def get_client_ip(self):
        """Get the client IP address from the request"""
        if not hasattr(self, 'request'):
            return None
            
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

    def get_user_agent(self):
        """Get the user agent from the request"""
        if not hasattr(self, 'request'):
            return None
        return self.request.META.get('HTTP_USER_AGENT', '')


    def log_save(self, sender, instance, created, **kwargs):
        if sender == SystemLog:
            return

        action = SystemLog.ACTION_CREATE if created else SystemLog.ACTION_UPDATE

        current_state = {}
        for field in instance._meta.fields:
            value = getattr(instance, field.name)
            current_state[field.name] = serialize_value(value)

        previous_state = None
        changes = None

        if not created and hasattr(instance, '_pre_save_state') and instance._pre_save_state:
            previous_state = instance._pre_save_state
            changes = {}
            for field, new_value in current_state.items():
                old_value = previous_state.get(field)
                if old_value != new_value:
                    changes[field] = {
                        'old': old_value,
                        'new': new_value
                    }

        SystemLog.objects.create(
            user=self.get_user(),
            action=action,
            model_name=f"{sender._meta.app_label}.{sender.__name__}",
            object_id=str(instance.pk),
            ip_address=self.get_client_ip(),
            user_agent=self.get_user_agent(),
            before_state=previous_state,
            after_state=current_state,
            changes=changes
        )


    def log_delete(self, sender, instance, **kwargs):
        """Handle post_delete signal to log delete operations"""
        # Skip if this is the SystemLog model to prevent recursion
        if sender == SystemLog:
            return

        # Get the state before deletion
        previous_state = {}
        for field in instance._meta.fields:
            value = getattr(instance, field.name)
            previous_state[field.name] = serialize_value(value)

        
        print("attempting to write the logs")
        SystemLog.objects.create(
            user=self.get_user(),
            action=SystemLog.ACTION_DELETE,
            model_name=f"{sender._meta.app_label}.{sender.__name__}",
            object_id=str(instance.pk),
            ip_address=self.get_client_ip(),
            user_agent=self.get_user_agent(),
            before_state=previous_state,
            after_state=None
        )

    def process_exception(self, request, exception):
        """Optional: Log exceptions if needed"""
        pass
    
    
class JWTAuthenticationMiddleware:
    """
    Graphene middleware for handling JWT authentication with detailed logging
    and non-breaking error handling.
    """

    def resolve(self, next, root, info, **kwargs):
        request = info.context
        auth_header = request.headers.get("Authorization", "")
        user = AnonymousUser()

        if not auth_header:
            logger.info("Authorization header is missing.")
        elif not auth_header.startswith("Bearer "):
            logger.warning("Authorization header must start with 'Bearer '.")
        else:
            token = auth_header.split("Bearer ")[1]
            try:
                decoded_data = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                print(decoded_data)
                phone_number = decoded_data.get("phone_number")
                if not phone_number:
                    logger.warning("Token decoded but 'phone_number' is missing.")
                else:
                    User = get_user_model()
                    user_obj = User.objects.filter(phone_number=phone_number).first()
                    if user_obj:
                        user = user_obj
                        logger.info(f"Authenticated user: {user.email}")
                    else:
                        logger.warning(f"No user found with id {phone_number} from token.")
            except jwt.ExpiredSignatureError:
                logger.warning("JWT token has expired.")
            except jwt.InvalidTokenError:
                logger.warning("JWT token is invalid.")
            except Exception as e:
                logger.error(f"Unexpected error while decoding JWT token: {str(e)}")

        request.user = user
        info.context.user = user
        return next(root, info, **kwargs)
