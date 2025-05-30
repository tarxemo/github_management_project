# decorators.py
from functools import wraps
from django.contrib.auth.models import AnonymousUser
from graphql import GraphQLError

def role_required(allowed_roles):
    """
    Decorator to restrict access to users with specific roles.

    :param allowed_roles: List or tuple of allowed role strings
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, info, *args, **kwargs):
            user = info.context.user

            if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
                raise GraphQLError("Authentication credentials were not provided.")

            if user.role not in allowed_roles:
                raise GraphQLError(f"Access denied. Allowed roles: {', '.join(allowed_roles)}")

            return func(self, info, *args, **kwargs)
        return wrapper
    return decorator
