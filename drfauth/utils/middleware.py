import datetime
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils.timezone import now


class AutoLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip if the user is not authenticated
        if request.user.is_authenticated:
            # Get the last activity time from the session
            last_activity = request.session.get('last_activity')
            current_time = now()

            # Check if the session has expired
            if last_activity:
                elapsed_time = (current_time - datetime.datetime.fromisoformat(last_activity)).total_seconds()
                if elapsed_time > settings.SESSION_COOKIE_AGE:
                    logout(request)
                    return redirect('login')  # Redirect to the login page after logout

            # Update the last activity time in the session
            request.session['last_activity'] = current_time.isoformat()

        return self.get_response(request)
