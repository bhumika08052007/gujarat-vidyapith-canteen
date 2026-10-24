from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db import models

class EmailAuthBackend(ModelBackend):
    """
    Authenticate using e-mail address.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        # Try finding by username first, then by email
        users = User.objects.filter(models.Q(email__iexact=username) | models.Q(username__iexact=username))
        for user in users:
            if user.check_password(password):
                return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
