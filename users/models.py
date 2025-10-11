from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField("Email", unique=True)
    phone = models.CharField("Телефон", max_length=20, blank=True)
    avatar = models.ImageField("Аватар", upload_to="avatars/", blank=True, null=True)
    is_organizer = models.BooleanField("Организатор", default=False)

    def __str__(self):
        return self.username
