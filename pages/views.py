import logging
from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.shortcuts import render, redirect
from django.template.loader import render_to_string

from .forms import ContactForm

logger = logging.getLogger('mail')

def home(request):
    return render(request, 'pages/home.html')

def about(request):
    return render(request, 'pages/about.html')

def contacts(request):
    initial = {}
    if request.user.is_authenticated:
        initial = {
            'name': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
        }

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            if request.user.is_authenticated:
                obj.user = request.user
            obj.save()

            # Опциональная нотификация на почту (не ломает UX при ошибках)
            try:
                notify_to = getattr(settings, 'CONTACTS_NOTIFY_EMAILS', None)
                if not notify_to:
                    # по умолчанию шлём на DEFAULT_FROM_EMAIL, если он указан
                    default = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
                    notify_to = [default] if default else []

                if notify_to:
                    ctx = {'m': obj, 'site_name': settings.SITE_NAME, 'site_url': settings.SITE_URL}
                    body = render_to_string('pages/contact_email.txt', ctx)
                    subj = f"[Контакты] {obj.subject}"
                    email = EmailMessage(subj, body, settings.DEFAULT_FROM_EMAIL, notify_to)
                    # чтобы можно было ответить прямо на письмо
                    if obj.email:
                        email.reply_to = [obj.email]
                    email.send(fail_silently=True)
            except Exception as e:
                logger.exception("Contact notify email failed: %s", e)

            messages.success(request, "Спасибо! Ваше сообщение отправлено.")
            return redirect('pages:contacts')
    else:
        form = ContactForm(initial=initial)

    return render(request, 'pages/contacts.html', {'form': form})
