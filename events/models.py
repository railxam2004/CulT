from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from datetime import timedelta

# генерация уникального слага
def generate_unique_slug(instance, value, slug_field_name: str = 'slug', max_len: int = 60) -> str:
    base = slugify(value) or 'event'
    base = base[:max_len]
    slug = base
    Model = instance.__class__
    n = 2
    # Проверяем, есть ли уже объект с таким слагом, если есть, добавляем суффикс
    while Model.objects.filter(**{slug_field_name: slug}).exclude(pk=instance.pk).exists():
        suffix = f'-{n}'
        slug = (base[:max_len - len(suffix)] + suffix)
        n += 1
    return slug

# категории мероприятий
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

# тарифы мероприятий
class Tariff(models.Model):
    name = models.CharField('Название тарифа', max_length=120, unique=True)
    description = models.TextField('Описание', blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Тариф'
        verbose_name_plural = 'Тарифы'

    def __str__(self):
        return self.name

# мероприятия
class Event(models.Model):
    # Статусы мероприятия
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        PENDING = 'pending', 'На модерации'
        PUBLISHED = 'published', 'Опубликовано'
        REJECTED = 'rejected', 'Отклонено'

    title = models.CharField('Название', max_length=255)
    slug = models.SlugField('Слаг', max_length=140, unique=True)
    image = models.ImageField('Афиша', upload_to='events/', blank=True, null=True)
    # Связь с категорией (при удалении категории мероприятия остаются - PROTECT)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='events', verbose_name='Категория'
    )
    # Связь с организатором
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='organized_events',
        verbose_name='Организатор',
        limit_choices_to={'is_organizer': True}, # чтобы нельзя было выбрать обычного пользователя
    )
    
    description = models.TextField('Описание', blank=True)
    starts_at = models.DateTimeField('Дата и время начала')
    # Длительность в минутах. может быть null, если длительность неизвестна
    duration_minutes = models.PositiveIntegerField('Длительность, мин', blank=True, null=True)
    location = models.CharField('Локация', max_length=255)

    status = models.CharField('Статус', max_length=20, choices=Status.choices, default=Status.DRAFT)
    # Кто проверял (модератор)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Модератор',
        related_name='moderated_events',
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    moderation_comment = models.TextField('Комментарий модератора', blank=True)
    # Общая вместимость (если задана, используется для расчета лимита билетов)
    capacity = models.PositiveIntegerField('Общая вместимость', blank=True, null=True)
    #общее количество доступных билетов по всем тарифам
    available_tickets = models.PositiveIntegerField('Остаток билетов (денорм.)', default=0)
    views_count = models.PositiveIntegerField('Просмотры', default=0)
    is_active = models.BooleanField('Активно', default=True)

    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    published_at = models.DateTimeField('Опубликовано', blank=True, null=True)

    RESERVED_SLUGS = {"my-events", "category", "scan"} # Зарезервированные слаги, которые нельзя использовать для мероприятий

    class Meta:
        ordering = ['-starts_at']
        verbose_name = 'Мероприятие'
        verbose_name_plural = 'Мероприятия'
        indexes = [
            models.Index(fields=['slug']), # Индекс для быстрого поиска по слагу
            models.Index(fields=['status', 'starts_at']), # Индекс для фильтрации по статусу и сортировки по дате
        ]

    def __str__(self):
        return self.title

    # Проверка перед сохранением
    def clean(self):
        # запретим зарезервированные слаги
        if self.slug and self.slug in self.RESERVED_SLUGS:
            raise ValidationError({'slug': "Этот слаг зарезервирован системой."})
    # Переопределение метода save для автоматической генерации слага
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.title, max_len=140) 
        super().save(*args, **kwargs)

    @property
    def ends_at(self):
        #Время окончания = starts_at + duration_minutes (если задана).
        if getattr(self, "duration_minutes", None):
            return self.starts_at + timedelta(minutes=self.duration_minutes)
        return self.starts_at

    @property
    def is_past(self) -> bool:
        #Событие считается прошедшим, если время окончания < сейчас.
        end = self.ends_at or self.starts_at
        return end < timezone.now()

    @property
    def is_buyable(self) -> bool:
        #Можно ли покупать билеты на событие сейчас
        return (
            self.status == self.Status.PUBLISHED
            and self.is_active
            and not self.is_past
            and (self.available_tickets or 0) > 0
        )

# Конкретный тариф для конкретного мероприятия (цена, квота)
class EventTariff(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='event_tariffs', verbose_name='Событие')
    tariff = models.ForeignKey(Tariff, on_delete=models.PROTECT, related_name='event_tariffs', verbose_name='Тариф')

    price = models.DecimalField('Цена', max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    available_quantity = models.PositiveIntegerField('Квота', validators=[MinValueValidator(0)])
    sales_count = models.PositiveIntegerField('Продано', default=0)
    is_active = models.BooleanField('Активно', default=True)

    class Meta:
        # Комбинация события и тарифа должна быть уникальной
        unique_together = [('event', 'tariff')]
        verbose_name = 'Тариф события'
        verbose_name_plural = 'Тарифы события'

    def __str__(self):
        return f'{self.event.title} — {self.tariff.name}'
    
    @property
    def remaining(self):
        aq = self.available_quantity or 0
        sc = self.sales_count or 0
        # Возвращаем разницу, но не меньше нуля
        return max(aq - sc, 0)


# заявки на правку события организатором
class EventEditRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "На модерации"
        APPROVED = "approved", "Одобрено"
        REJECTED = "rejected", "Отклонено"

    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='edit_requests')
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='event_edit_requests')

    # Поля с новыми значениями, которые хочет применить организатор
    new_description = models.TextField()
    new_category = models.ForeignKey(Category, on_delete=models.PROTECT) 
    new_image = models.ImageField(upload_to='event_edits/', blank=True, null=True)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    comment = models.TextField(blank=True) # комментарий модератора
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    # Модератор, который проверил заявку
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True,
                                    on_delete=models.SET_NULL, related_name='reviewed_event_edits')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Заявка на правку события'
        verbose_name_plural = 'Заявки на правку событий'
        constraints = [
            # не более одной активной заявки на событие
            models.UniqueConstraint(
                fields=['event'],
                condition=Q(status='pending'),
                name='uniq_pending_edit_per_event'
            )
        ]

    def __str__(self):
        return f"Правки для {self.event} от {self.submitted_by} ({self.get_status_display()})"
    
# Прокси-модель для событий на модерации
class PendingEvent(Event):
    class Meta:
        proxy = True
        verbose_name = "Событие на модерации"
        verbose_name_plural = "События на модерации"
