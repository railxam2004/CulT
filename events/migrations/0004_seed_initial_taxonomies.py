from django.db import migrations

def seed_forward(apps, schema_editor):
    Category = apps.get_model('events', 'Category')
    Tariff = apps.get_model('events', 'Tariff')

    categories = [
        ('Выставки', 'exhibitions'),
        ('Детские мероприятия', 'kids'),
        ('Кино', 'cinema'),
        ('Концерты', 'concerts'),
        ('Лекции и мастер-классы', 'lectures'),
        ('Прочее', 'other'),
        ('Семинары и конференции', 'conferences'),
        ('Спорт', 'sport'),
        ('Театр', 'theatre'),
        ('Фестивали', 'festivals'),
    ]
    for name, slug in categories:
        Category.objects.get_or_create(slug=slug, defaults={'name': name})

    tariffs = [
        'VIP',
        'Бесплатный',
        'Премиум',
        'Стандарт',
        'Студенческий',
    ]
    for name in tariffs:
        Tariff.objects.get_or_create(name=name)

def seed_backward(apps, schema_editor):
    Category = apps.get_model('events', 'Category')
    Tariff = apps.get_model('events', 'Tariff')
    slugs = ['exhibitions','kids','cinema','concerts','lectures','other','conferences','sport','theatre','festivals']
    Category.objects.filter(slug__in=slugs).delete()
    Tariff.objects.filter(name__in=['VIP','Бесплатный','Премиум','Стандарт','Студенческий']).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('events', '0003_eventeditrequest'),
    ]
    operations = [
        migrations.RunPython(seed_forward, reverse_code=seed_backward),
    ]

