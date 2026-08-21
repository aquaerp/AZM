from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from rest_framework.exceptions import ValidationError


def fernet():
    if not settings.DOCUMENT_ENCRYPTION_KEY:
        raise ValidationError("مفتاح تشفير الوثائق غير مهيأ.")
    try:
        return Fernet(settings.DOCUMENT_ENCRYPTION_KEY.encode())
    except (ValueError, TypeError) as error:
        raise ValidationError("مفتاح تشفير الوثائق غير صالح.") from error


def encrypt(data: bytes) -> bytes:
    return fernet().encrypt(data)


def decrypt(data: bytes) -> bytes:
    try:
        return fernet().decrypt(data)
    except InvalidToken as error:
        raise ValidationError("تعذر فك تشفير الملف. تحقق من مفتاح التشفير.") from error
