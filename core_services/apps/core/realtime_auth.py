from urllib.parse import parse_qs

from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

_jwt_authentication = JWTAuthentication()


@database_sync_to_async
def _authenticate_token(token):
    if not token:
        return AnonymousUser(), {}

    try:
        validated_token = _jwt_authentication.get_validated_token(token)
        user = _jwt_authentication.get_user(validated_token)
        return user, dict(validated_token.payload)
    except (InvalidToken, TokenError):
        return AnonymousUser(), {}


class QueryStringJWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token = (params.get("token") or [""])[0]
        scope["user"] = AnonymousUser()
        scope["token_payload"] = {}

        if token:
            scope["user"], scope["token_payload"] = await _authenticate_token(token)

        return await super().__call__(scope, receive, send)
