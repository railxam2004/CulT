from django import forms
from django.contrib import admin
from django.contrib.admin.helpers import ActionForm
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, OrganizerApplication


class OrganizerActionForm(ActionForm):
    """Форма действий с полем комментария."""
    comment = forms.CharField(
        required=False,
        label="Комментарий (для отклонения)",
        widget=forms.Textarea(attrs={"rows": 2})
    )


@admin.action(description="Одобрить заявки и выдать статус организатора")
def approve_applications(modeladmin, request, queryset):
    count = 0
    for app in queryset.select_related("user"):
        app.status = OrganizerApplication.Status.APPROVED
        app.save(update_fields=['status'])
        if not app.user.is_organizer:
            app.user.is_organizer = True
            app.user.save(update_fields=['is_organizer'])
        count += 1
    modeladmin.message_user(request, f"Одобрено заявок: {count}")


@admin.action(description="Отклонить заявки (с комментарием)")
def reject_applications(modeladmin, request, queryset):
    comment = request.POST.get("comment", "").strip()
    updated = 0
    for app in queryset:
        app.status = OrganizerApplication.Status.REJECTED
        if comment:
            app.comment = comment
            app.save(update_fields=['status', 'comment'])
        else:
            app.save(update_fields=['status'])
        updated += 1
    modeladmin.message_user(request, f"Отклонено заявок: {updated}")


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Дополнительно", {"fields": ("phone", "avatar", "is_organizer")}),
    )
    list_display = ("username", "email", "is_organizer", "is_staff", "is_active")
    list_filter = ("is_organizer", "is_staff", "is_active")

    @admin.action(description="Назначить организатором")
    def make_organizer(self, request, queryset):
        updated = queryset.update(is_organizer=True)
        self.message_user(request, f"Назначено организаторов: {updated}")

    @admin.action(description="Снять статус организатора")
    def remove_organizer(self, request, queryset):
        updated = queryset.update(is_organizer=False)
        self.message_user(request, f"Снят статус организатора у: {updated}")

    actions = ["make_organizer", "remove_organizer"]


@admin.register(OrganizerApplication)
class OrganizerApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'company_name', 'inn', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'user__email', 'company_name', 'inn', 'phone')
    action_form = OrganizerActionForm
    actions = [approve_applications, reject_applications]
