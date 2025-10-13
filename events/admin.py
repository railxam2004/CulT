# events/admin.py
from django import forms
from django.contrib import admin
from django.contrib.admin.helpers import ActionForm
from django.utils import timezone
from .models import Category, Tariff, Event, EventTariff, EventEditRequest

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# --- проверка на активные тарифы ---
def event_has_active_tariff(event: Event) -> bool:
    for et in event.event_tariffs.filter(is_active=True):
        rem = max((et.available_quantity or 0) - (et.sales_count or 0), 0)
        if rem > 0:
            return True
    return False

# --- форма действий ---
class EventActionForm(ActionForm):
    comment = forms.CharField(
        required=False,
        label="Комментарий модератора",
        widget=forms.Textarea(attrs={"rows": 2})
    )

# --- actions ---
@admin.action(description="Отправить на модерацию")
def mark_pending(modeladmin, request, queryset):
    updated = 0
    for ev in queryset:
        if ev.status in (Event.Status.DRAFT, Event.Status.REJECTED):
            ev.status = Event.Status.PENDING
            ev.moderation_comment = ""
            ev.moderated_by = None
            ev.save(update_fields=["status", "moderation_comment", "moderated_by"])
            updated += 1
    modeladmin.message_user(request, f"На модерацию отправлено: {updated}")

@admin.action(description="Опубликовать (одобрить)")
def publish_events(modeladmin, request, queryset):
    approved = 0
    skipped = 0
    for ev in queryset:
        if not event_has_active_tariff(ev):
            skipped += 1
            continue
        ev.status = Event.Status.PUBLISHED
        ev.published_at = timezone.now()
        ev.moderated_by = request.user
        ev.moderation_comment = ""
        ev.save(update_fields=["status", "published_at", "moderated_by", "moderation_comment"])
        approved += 1
    msg = f"Опубликовано: {approved}"
    if skipped:
        msg += f". Пропущено (нет активных тарифов с остатком): {skipped}"
    modeladmin.message_user(request, msg)

@admin.action(description="Отклонить (с комментарием)")
def reject_events(modeladmin, request, queryset):
    comment = request.POST.get("comment", "").strip()
    updated = 0
    for ev in queryset:
        ev.status = Event.Status.REJECTED
        ev.moderated_by = request.user
        if comment:
            ev.moderation_comment = comment
            ev.save(update_fields=["status", "moderated_by", "moderation_comment"])
        else:
            ev.save(update_fields=["status", "moderated_by"])
        updated += 1
    modeladmin.message_user(request, f"Отклонено: {updated}")

@admin.action(description="Вернуть в черновик")
def mark_draft(modeladmin, request, queryset):
    updated = queryset.update(
        status=Event.Status.DRAFT,
        moderated_by=None,
        moderation_comment="",
    )
    modeladmin.message_user(request, f"В черновики переведено: {updated}")

# --- inline ---
class EventTariffInline(admin.TabularInline):
    model = EventTariff
    extra = 1
    fields = ('tariff', 'price', 'available_quantity', 'sales_count', 'is_active')
    readonly_fields = ('sales_count',)

# --- основной класс EventAdmin ---
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'organizer', 'starts_at', 'status', 'available_tickets', 'is_active')
    list_filter = ('status', 'category', 'is_active')
    search_fields = ('title', 'description', 'location')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [EventTariffInline]

    readonly_fields = ('published_at', 'moderated_by', 'views_count')

    fieldsets = (
        (None, {
            "fields": ("title", "slug", "image", "category", "organizer", "description",
                       "starts_at", "duration_minutes", "location")
        }),
        ("Публикация", {
            "fields": ("status", "is_active", "available_tickets",
                       "published_at", "moderated_by", "moderation_comment")
        }),
        ("Системные", {
            "fields": ("views_count",),
        }),
    )

    action_form = EventActionForm
    actions = [mark_pending, publish_events, reject_events, mark_draft]

# --- АДМИНКА ДЛЯ EVENTEDITREQUEST ---
@admin.register(EventEditRequest)
class EventEditRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'event', 'submitted_by', 'status', 'created_at', 'reviewed_at')
    list_filter = ('status', 'created_at', 'new_category')
    search_fields = ('event__title', 'submitted_by__username', 'submitted_by__email')
    # Добавил 'new_description' и 'new_image' для просмотра в деталях, но сделал readonly
    readonly_fields = ('event', 'submitted_by', 'created_at', 'reviewed_at', 'reviewed_by',
                       'new_description', 'new_category', 'new_image')
    actions = ['approve_requests', 'reject_requests']
    
    # Чтобы поля были видны в админке
    fieldsets = (
        (None, {
            "fields": ('event', 'submitted_by', 'status', 'created_at', 'reviewed_at', 'reviewed_by', 'comment'),
        }),
        ("Предложенные изменения", {
            "fields": ('new_description', 'new_category', 'new_image'),
        }),
    )

    @admin.action(description="Одобрить выбранные изменения")
    def approve_requests(self, request, queryset):
        qs = queryset.filter(status=EventEditRequest.Status.PENDING)
        count = 0
        for req in qs.select_related('event', 'new_category'):
            e = req.event
            # применяем поля
            e.description = req.new_description
            e.category = req.new_category
            if req.new_image:
                # Если новое изображение загружено, заменяем его.
                e.image = req.new_image
            # Сохраняем событие
            e.save(update_fields=['description', 'category', 'image'])
            
            # помечаем заявку
            req.status = EventEditRequest.Status.APPROVED
            req.reviewed_by = request.user
            req.reviewed_at = timezone.now()
            req.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
            count += 1
        self.message_user(request, f"Одобрено заявок: {count}")

    @admin.action(description="Отклонить выбранные изменения")
    def reject_requests(self, request, queryset):
        qs = queryset.filter(status=EventEditRequest.Status.PENDING)
        updated = qs.update(
            status=EventEditRequest.Status.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f"Отклонено заявок: {updated}")