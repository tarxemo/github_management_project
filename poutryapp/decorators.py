# decorators.py
from functools import wraps
from django.contrib.auth.models import AnonymousUser
from graphql import GraphQLError

def skip_auth(resolver_func):
    resolver_func.skip_auth = True
    return resolver_func

