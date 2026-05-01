import zoneinfo
from django.utils import timezone

class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            tzname = None
            if request.user.is_parent and request.user.household_timezone:
                tzname = request.user.household_timezone
            elif request.user.is_kid and request.user.parent_account and request.user.parent_account.household_timezone:
                tzname = request.user.parent_account.household_timezone
            
            if tzname:
                try:
                    timezone.activate(zoneinfo.ZoneInfo(tzname))
                except Exception:
                    timezone.deactivate()
            else:
                timezone.deactivate()
        else:
            timezone.deactivate()
        
        return self.get_response(request)
