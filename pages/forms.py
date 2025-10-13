from django import forms
from .models import ContactMessage

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']
        labels = {
            'name': 'Ваше имя',
            'email': 'Email',
            'phone': 'Телефон',
            'subject': 'Тема',
            'message': 'Сообщение',
        }
        widgets = {
            'message': forms.Textarea(attrs={'rows': 6}),
        }

    def clean(self):
        data = super().clean()
        email = (data.get('email') or '').strip()
        phone = (data.get('phone') or '').strip()
        if not email and not phone:
            raise forms.ValidationError("Укажите хотя бы один способ связи: email или телефон.")
        return data
