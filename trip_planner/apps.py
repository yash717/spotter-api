from django.apps import AppConfig


class TripPlannerConfig(AppConfig):
    name = "trip_planner"

    def ready(self):
        # Register drf-spectacular extension for CookieJWTAuthentication so Swagger/ReDoc show it
        from trip_planner import schema  # noqa: F401
