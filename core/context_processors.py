from django.conf import settings as django_settings


def app_settings(request):
    return {
        'APP_NAME': django_settings.APP_NAME,
        'APP_TAGLINE': django_settings.APP_TAGLINE,
        'APP_ICON': django_settings.APP_ICON,
    }
