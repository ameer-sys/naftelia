import os
from functools import wraps

import jwt
from flask import g, jsonify, request
from jwt import PyJWKClient


class AuthError(Exception):
    def __init__(self, message, status_code=401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class Auth0Verifier:
    def __init__(self):
        self.domain = os.getenv("AUTH0_DOMAIN", "").strip().rstrip("/")
        self.audience = os.getenv("AUTH0_AUDIENCE", "").strip()
        self.demo_auth = os.getenv("NAFTELIA_DEMO_AUTH", "false").lower() == "true"
        self._jwks_client = None

    @property
    def configured(self):
        return bool(self.domain and self.audience and "your-" not in self.domain)

    @property
    def issuer(self):
        return f"https://{self.domain}/"

    def demo_claims(self):
        return {
            "sub": "demo-captain",
            "email": "captain@naftelia.local",
            "name": "Demo Captain",
        }

    def verify_request(self):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            if self.demo_auth:
                return self.demo_claims()
            raise AuthError("Missing bearer token")

        if not self.configured:
            raise AuthError("Auth0 is not configured", 500)

        token = auth_header.split(" ", 1)[1].strip()
        if self._jwks_client is None:
            self._jwks_client = PyJWKClient(f"{self.issuer}.well-known/jwks.json")

        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
            )
        except jwt.PyJWTError as exc:
            raise AuthError(str(exc)) from exc


auth0 = Auth0Verifier()


def require_auth(route):
    @wraps(route)
    def wrapper(*args, **kwargs):
        try:
            g.user_claims = auth0.verify_request()
        except AuthError as exc:
            return jsonify({"error": exc.message}), exc.status_code
        return route(*args, **kwargs)

    return wrapper
