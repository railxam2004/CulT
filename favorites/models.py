from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint
from events.models import Event

class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['user', 'event'], name='uniq_favorite_user_event'),
        ]
        ordering = ['-created_at']
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'

    def __str__(self) -> str:
        return f"{self.user} → {self.event}"
