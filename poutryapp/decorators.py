from functools import wraps
from graphql import GraphQLError

def require_authentication(func):
    @wraps(func)
    def wrapper(self, info, *args, **kwargs):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        return func(self, info, *args, **kwargs)
    return wrapper
