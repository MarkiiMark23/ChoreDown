import secrets
import string

from django.db import migrations, models

_ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'


def _generate_code():
    return ''.join(secrets.choice(_ALPHABET) for _ in range(6))


def populate_family_codes(apps, schema_editor):
    CustomUser = apps.get_model('core', 'CustomUser')
    used = set(
        CustomUser.objects.exclude(family_code='').values_list('family_code', flat=True)
    )
    for user in CustomUser.objects.filter(family_code=''):
        code = _generate_code()
        while code in used:
            code = _generate_code()
        used.add(code)
        user.family_code = code
        user.save(update_fields=['family_code'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_alter_notification_notification_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='family_code',
            field=models.CharField(blank=True, default='', max_length=6),
            preserve_default=False,
        ),
        migrations.RunPython(populate_family_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='customuser',
            name='family_code',
            field=models.CharField(blank=True, max_length=6, unique=True),
        ),
    ]
