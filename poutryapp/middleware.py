# middleware.py
import jwt
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)

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
