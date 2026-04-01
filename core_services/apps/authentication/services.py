from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer, MeSerializer


def generate_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    refresh["role"] = user.role
    refresh["company_id"] = str(user.company_id) if user.company_id else None

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def get_login_identifier(data):
    return (
        data.get("identifier")
        or data.get("email")
        or data.get("mobile_number")
        or ""
    ).strip()


def validate_login_request(data):
    serializer = LoginSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data["user"]


def _login_attempt_key(email):
    return f"login_attempt:{email.lower()}"


def is_login_allowed(email, max_attempts=5):
    attempts = cache.get(_login_attempt_key(email), 0)
    return attempts < max_attempts


def increment_login_attempt(email, timeout_seconds=300):
    key = _login_attempt_key(email)
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, timeout=timeout_seconds)


def reset_login_attempts(email):
    cache.delete(_login_attempt_key(email))


def get_user_cache(user):
    key = f"user_profile:{user.id}"
    cached = cache.get(key)

    if cached:
        return cached

    data = MeSerializer(user).data
    cache.set(key, data, timeout=300)
    return data


def invalidate_user_cache(user_id):
    cache.delete(f"user_profile:{user_id}")
