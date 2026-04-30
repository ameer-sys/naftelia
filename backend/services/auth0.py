from functools import wraps
from flask import g, jsonify, request


class AuthError(Exception):
    def __init__(self, message, status_code=401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class DemoAuthVerifier:
    """Simple hardcoded demo authentication."""
    def demo_claims(self):
        return {
            "sub": "demo-captain",
            "email": "captain@naftelia.local",
            "name": "Demo Captain",
        }

    def verify_request(self):
        # Always return demo claims (no token validation)
        return self.demo_claims()


auth_verifier = DemoAuthVerifier()


def require_auth(route):
    @wraps(route)
    def wrapper(*args, **kwargs):
        try:
            g.user_claims = auth_verifier.verify_request()
        except AuthError as exc:
            return jsonify({"error": exc.message}), exc.status_code
        return route(*args, **kwargs)

    return wrapper
