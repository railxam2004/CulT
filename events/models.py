from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError # Added for clean method

# --- генерация уникального slug ---
def generate_unique_slug(instance, value, slug_field_name: str = 'slug', max_len: int = 60) -> str:
    base = slugify(value) or 'event'
    base = base[:max_len]
    slug = base
    Model = instance.__class__
    n = 2
    # The original Event model had max_length=140 for slug, so we use it here if provided, but default max_len is 60.
    # The Event model below has max_length=140.
    while Model.objects.filter(**{slug_field_name: slug}).exclude(pk=instance.pk).exists():
        suffix = f'-{n}'
        slug = (base[:max_len - len(suffix)] + suffix)
        n += 1
    return slug


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
    # Changed slug to not have default db_index, as it's included in 'slug' index below.
    # But it must be unique. Retained original max_length=140.
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
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Модератор',
        related_name='moderated_events',
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    moderation_comment = models.TextField('Комментарий модератора', blank=True)
    capacity = models.PositiveIntegerField('Общая вместимость', blank=True, null=True)
    available_tickets = models.PositiveIntegerField('Остаток билетов (денорм.)', default=0)
    views_count = models.PositiveIntegerField('Просмотры', default=0)
    is_active = models.BooleanField('Активно', default=True)

    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    published_at = models.DateTimeField('Опубликовано', blank=True, null=True)

    RESERVED_SLUGS = {"my-events", "category", "scan"} # Added for clean method

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

    def clean(self):
        # запретим зарезервированные слаги
        if self.slug and self.slug in self.RESERVED_SLUGS:
            # from django.core.exceptions import ValidationError - already imported
            raise ValidationError({'slug': "Этот слаг зарезервирован системой."})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.title, max_len=140) # Used max_len=140 from the model's SlugField
        super().save(*args, **kwargs)


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
    
    @property
    def remaining(self):
        aq = self.available_quantity or 0
        sc = self.sales_count or 0
        return max(aq - sc, 0)


# --- заявки на правку события организатором ---
class EventEditRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "На модерации"
        APPROVED = "approved", "Одобрено"
        REJECTED = "rejected", "Отклонено"

    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='edit_requests')
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='event_edit_requests')

    new_description = models.TextField()
    # Note: the new Category model definition is implicitly referenced here as it exists above.
    # To avoid circular import issues if Category was defined elsewhere, 'Category' is often used as a string.
    # Since all models are in the same file, 'Category' (string) or Category (direct reference) works.
    new_category = models.ForeignKey(Category, on_delete=models.PROTECT) 
    new_image = models.ImageField(upload_to='event_edits/', blank=True, null=True)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True,
                                    on_delete=models.SET_NULL, related_name='reviewed_event_edits')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Заявка на правку события' # Added for completeness
        verbose_name_plural = 'Заявки на правку событий' # Added for completeness
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