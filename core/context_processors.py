from django.conf import settings as django_settings


def app_settings(request):
    unread_notifications = 0
    if request.user.is_authenticated:
        unread_notifications = request.user.notifications.filter(
            deliver_in_app=True,
            is_read=False,
        ).count()
    return {
        'APP_NAME': django_settings.APP_NAME,
        'APP_TAGLINE': django_settings.APP_TAGLINE,
        'APP_ICON': django_settings.APP_ICON,
        'UNREAD_NOTIFICATIONS': unread_notifications,
    }
