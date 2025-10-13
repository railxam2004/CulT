from django.conf import settings
from django.db import models

class ContactMessage(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новое'
        IN_PROGRESS = 'in_progress', 'В работе'
        CLOSED = 'closed', 'Закрыто'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='contact_messages'
    )
    name = models.CharField('Имя', max_length=120)
    email = models.EmailField('Email', blank=True)
    phone = models.CharField('Телефон', max_length=32, blank=True)
    subject = models.CharField('Тема', max_length=200)
    message = models.TextField('Сообщение')
    status = models.CharField('Статус', max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Сообщение с контактов'
        verbose_name_plural = 'Сообщения с контактов'

    def __str__(self):
        tag = self.email or self.phone or 'нет контакта'
        return f"{self.subject} — {tag}"
