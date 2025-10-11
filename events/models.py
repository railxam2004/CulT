from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

class Category(models.Model):
    name = models.CharField('Название', max_length=120, unique=True)
    slug = models.SlugField('Слаг', max_length=140, unique=True)
    description = models.TextField('Описание', blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Tariff(models.Model):
    name = models.CharField('Название тарифа', max_length=120, unique=True)
    description = models.TextField('Описание', blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Тариф'
        verbose_name_plural = 'Тарифы'

    def __str__(self):
        return self.name


class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        PENDING = 'pending', 'На модерации'
        PUBLISHED = 'published', 'Опубликовано'
        REJECTED = 'rejected', 'Отклонено'

    title = models.CharField('Название', max_length=255)
    slug = models.SlugField('Слаг', max_length=140, unique=True)
    image = models.ImageField('Афиша', upload_to='events/', blank=True, null=True)

    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='events', verbose_name='Категория'
    )
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='organized_events',
        verbose_name='Организатор',
        limit_choices_to={'is_organizer': True},
    )

    description = models.TextField('Описание', blank=True)
    starts_at = models.DateTimeField('Дата и время начала')
    duration_minutes = models.PositiveIntegerField('Длительность, мин', blank=True, null=True)
    location = models.CharField('Локация', max_length=255)

    status = models.CharField('Статус', max_length=20, choices=Status.choices, default=Status.DRAFT)
    capacity = models.PositiveIntegerField('Общая вместимость', blank=True, null=True)
    available_tickets = models.PositiveIntegerField('Остаток билетов (денорм.)', default=0)
    views_count = models.PositiveIntegerField('Просмотры', default=0)
    is_active = models.BooleanField('Активно', default=True)

    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    published_at = models.DateTimeField('Опубликовано', blank=True, null=True)

    class Meta:
        ordering = ['-starts_at']
        verbose_name = 'Мероприятие'
        verbose_name_plural = 'Мероприятия'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status', 'starts_at']),
        ]

    def __str__(self):
        return self.title


class EventTariff(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='event_tariffs', verbose_name='Событие')
    tariff = models.ForeignKey(Tariff, on_delete=models.PROTECT, related_name='event_tariffs', verbose_name='Тариф')

    price = models.DecimalField('Цена', max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    available_quantity = models.PositiveIntegerField('Квота', validators=[MinValueValidator(0)])
    sales_count = models.PositiveIntegerField('Продано', default=0)
    is_active = models.BooleanField('Активно', default=True)

    class Meta:
        unique_together = [('event', 'tariff')]
        verbose_name = 'Тариф события'
        verbose_name_plural = 'Тарифы события'

    def __str__(self):
        return f'{self.event.title} — {self.tariff.name}'
