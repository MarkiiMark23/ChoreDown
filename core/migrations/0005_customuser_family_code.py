import secrets
import string

from django.db import migrations, models


def _generate_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(6))


def populate_family_codes(apps, schema_editor):
    CustomUser = apps.get_model('core', 'CustomUser')
    used = set()
    for user in CustomUser.objects.filter(family_code=''):
        code = _generate_code()
        while code in used or CustomUser.objects.filter(family_code=code).exists():
            code = _generate_code()
        used.add(code)
        user.family_code = code
        user.save(update_fields=['family_code'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_behavior_points_value_customuser_avatar_color_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='family_code',
            field=models.CharField(blank=True, max_length=6, default=''),
            preserve_default=False,
        ),
        migrations.RunPython(populate_family_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='customuser',
            name='family_code',
            field=models.CharField(blank=True, max_length=6, unique=True),
        ),
    ]
