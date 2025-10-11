from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models import Q, UniqueConstraint


class User(AbstractUser):
    email = models.EmailField("Email", unique=True)
    phone = models.CharField("Телефон", max_length=20, blank=True)
    avatar = models.ImageField("Аватар", upload_to="avatars/", blank=True, null=True)
    is_organizer = models.BooleanField("Организатор", default=False)

    def __str__(self):
        return self.username

class OrganizerApplication(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новая'
        IN_REVIEW = 'moderation', 'На модерации'
        APPROVED = 'approved', 'Одобрена'
        REJECTED = 'rejected', 'Отклонена'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organizer_applications',
        verbose_name='Пользователь'
    )
    company_name = models.CharField('Название организации', max_length=255)
    inn = models.CharField('ИНН', max_length=20)
    ogrn = models.CharField('ОГРН', max_length=20, blank=True)
    contact_email = models.EmailField('Контактный email')
    phone = models.CharField('Телефон', max_length=20)

    status = models.CharField(
        'Статус',
        max_length=20,
        choices=Status.choices,
        default=Status.NEW
    )
    comment = models.TextField('Комментарий модератора', blank=True)

    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Заявка организатора'
        verbose_name_plural = 'Заявки организаторов'
        # Только одна "активная" (NEW/MODERATION) заявка на пользователя
        constraints = [
            UniqueConstraint(
                fields=['user'],
                condition=Q(status__in=['new', 'moderation']),
                name='unique_active_organizer_application_per_user',
            )
        ]

    def __str__(self):
        return f'Заявка {self.user} ({self.get_status_display()})'