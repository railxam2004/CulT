# users/views.py
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy

from .forms import UserRegisterForm, UserUpdateForm, OrganizerApplicationForm
from .models import OrganizerApplication


def register(request):
    """Регистрация нового пользователя."""
    if request.user.is_authenticated:
        return redirect("users:profile")

    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Регистрация прошла успешно!")
            return redirect("pages:home")
    else:
        form = UserRegisterForm()

    return render(request, "users/register.html", {"form": form})


@login_required
def profile(request):
    active_statuses = [
        OrganizerApplication.Status.NEW,
        OrganizerApplication.Status.IN_REVIEW,
    ]
    # последняя заявка любого статуса (для инфо)
    last_app = (
        OrganizerApplication.objects
        .filter(user=request.user)
        .order_by('-created_at')
        .first()
    )
    # активная заявка (new/moderation), если есть
    last_active_app = (
        OrganizerApplication.objects
        .filter(user=request.user, status__in=active_statuses)
        .order_by('-created_at')
        .first()
    )
    has_active_app = last_active_app is not None

    context = {
        "last_app": last_app,
        "last_active_app": last_active_app,
        "has_active_app": has_active_app,
    }
    return render(request, "users/profile.html", context)


@login_required
def profile_edit(request):
    """Редактирование профиля (включая аватар)."""
    if request.method == "POST":
        form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Профиль обновлён.")
            return redirect("users:profile")
    else:
        form = UserUpdateForm(instance=request.user)
    return render(request, "users/profile_edit.html", {"form": form})


class MyPasswordChangeView(PasswordChangeView):
    template_name = "users/password_change.html"
    success_url = reverse_lazy("users:password_change_done")

    def form_valid(self, form):
        messages.success(self.request, "Пароль успешно изменён.")
        return super().form_valid(form)


class MyPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = "users/password_change_done.html"


@login_required
def organizer_request(request):
    # Если уже организатор — не даём подать повторно
    if request.user.is_organizer:
        messages.info(request, "Вы уже являетесь организатором.")
        return redirect("users:profile")

    active_statuses = [
        OrganizerApplication.Status.NEW,
        OrganizerApplication.Status.IN_REVIEW,
    ]
    if OrganizerApplication.objects.filter(user=request.user, status__in=active_statuses).exists():
        messages.info(request, "У вас уже есть активная заявка на рассмотрении.")
        return redirect("users:profile")

    if request.method == "POST":
        form = OrganizerApplicationForm(request.POST, user=request.user)
        if form.is_valid():
            app = form.save(commit=False)
            app.user = request.user
            app.status = OrganizerApplication.Status.NEW
            app.save()
            messages.success(request, "Заявка отправлена и будет рассмотрена администратором.")
            return redirect("users:profile")
    else:
        form = OrganizerApplicationForm(user=request.user)

    return render(request, "users/organizer_request.html", {"form": form})

