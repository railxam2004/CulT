from django.http import HttpResponse

def event_list(request):
    return HttpResponse("Список мероприятий (пока заглушка)")
