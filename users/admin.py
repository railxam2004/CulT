# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, OrganizerApplication

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Дополнительно", {"fields": ("phone", "avatar", "is_organizer")}),
    )
    list_display = ("username", "email", "is_organizer", "is_staff", "is_active")
    list_filter = ("is_organizer", "is_staff", "is_active")

@admin.action(description="Одобрить заявки и выдать статус организатора")
def approve_applications(modeladmin, request, queryset):
    count = 0
    for app in queryset:
        app.status = OrganizerApplication.Status.APPROVED
        app.save(update_fields=['status'])
        # Выдаем права организатора
        if not app.user.is_organizer:
            app.user.is_organizer = True
            app.user.save(update_fields=['is_organizer'])
        count += 1
    modeladmin.message_user(request, f"Одобрено заявок: {count}")

@admin.action(description="Отклонить заявки")
def reject_applications(modeladmin, request, queryset):
    updated = queryset.update(status=OrganizerApplication.Status.REJECTED)
    modeladmin.message_user(request, f"Отклонено заявок: {updated}")

@admin.register(OrganizerApplication)
class OrganizerApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'company_name', 'inn', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'user__email', 'company_name', 'inn', 'phone')
    actions = [approve_applications, reject_applications]
