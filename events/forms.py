from django import forms
from django.forms import inlineformset_factory
from django.utils.text import slugify

from .models import Event, EventTariff


class EventForm(forms.ModelForm):
    # Удобный ввод даты/времени
    starts_at = forms.DateTimeField(
        label="Дата и время начала",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )

    class Meta:
        model = Event
        fields = ["title", "image", "category", "description", "starts_at", "duration_minutes", "location"]

    def clean_title(self):
        return self.cleaned_data["title"].strip()

    def _generate_unique_slug(self, title: str) -> str:
        base = slugify(title)[:120] or "event"
        slug = base
        i = 2
        Model = self._meta.model
        while Model.objects.filter(slug=slug).exists():
            slug = f"{base}-{i}"
            i += 1
        return slug

    def save(self, organizer, commit=True):
        """Сохраняем событие и назначаем организатора.
        Если slug пуст, подключим автогенерацию.
        """
        event = super().save(commit=False)
        if not event.slug:
            event.slug = self._generate_unique_slug(event.title)
        if not event.pk:
            event.organizer = organizer
        if commit:
            event.save()
        return event


class EventTariffForm(forms.ModelForm):
    class Meta:
        model = EventTariff
        fields = ["tariff", "price", "available_quantity", "is_active"]


EventTariffFormSet = inlineformset_factory(
    parent_model=Event,
    model=EventTariff,
    form=EventTariffForm,
    extra=0,            # без лишних пустых форм
    can_delete=True,
    min_num=1,          # опционально: хотя бы один тариф
    validate_min=False  # можно True, если хочешь строго требовать ≥1
)

