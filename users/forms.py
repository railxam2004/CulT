# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from .models import OrganizerApplication

User = get_user_model()


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(label="Email", required=True)
    first_name = forms.CharField(label="Имя", required=False)
    last_name = forms.CharField(label="Фамилия", required=False)
    phone = forms.CharField(label="Телефон", required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name", "phone")

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise ValidationError("Пользователь с таким email уже существует.")
        return email


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(label="Email", required=True)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "phone", "avatar")

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        qs = User.objects.filter(email=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Этот email уже используется другим аккаунтом.")
        return email


class OrganizerApplicationForm(forms.ModelForm):
    class Meta:
        model = OrganizerApplication
        fields = (
            "company_name",
            "inn",
            "ogrn",
            "contact_email",
            "phone",
        )
        labels = {
            "company_name": "Название организации",
            "inn": "ИНН",
            "ogrn": "ОГРН (опционально)",
            "contact_email": "Контактный email",
            "phone": "Телефон",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # Подставим значения по умолчанию из профиля
        if self.user:
            if not self.initial.get("contact_email"):
                self.initial["contact_email"] = self.user.email or ""
            if not self.initial.get("phone"):
                self.initial["phone"] = getattr(self.user, "phone", "") or ""

    def clean(self):
        cleaned = super().clean()
        user = self.user
        if user is None:
            return cleaned
        # Запретить повторную активную заявку (new/moderation)
        active_statuses = [
            OrganizerApplication.Status.NEW,
            OrganizerApplication.Status.IN_REVIEW,
        ]
        if OrganizerApplication.objects.filter(user=user, status__in=active_statuses).exists():
            raise ValidationError("У вас уже есть активная заявка на рассмотрении.")
        return cleaned
