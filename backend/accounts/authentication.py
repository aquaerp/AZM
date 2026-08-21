from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import workshop_has_valid_subscription


class SessionVersionJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if validated_token.get("session_version", 0) != user.session_version:
            raise AuthenticationFailed("انتهت صلاحية الجلسة بعد تغيير الحساب أو صلاحياته.", code="session_revoked")
        if not workshop_has_valid_subscription(user.workshop):
            raise AuthenticationFailed("اشتراك الورشة غير نشط أو انتهت مدته.", code="subscription_inactive")
        return user
