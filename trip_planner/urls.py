from django.urls import path

from .views import (
    GeocodeAutocompleteView,
    InvitationAcceptView,
    InvitationDetailView,
    InvitationListCreateView,
    InvitationResendView,
    InvitationRevokeView,
    InvitationValidateView,
    LoginView,
    LogoutView,
    MemberDetailView,
    MemberListView,
    MeView,
    OrganizationDetailView,
    ProfileView,
    RefreshView,
    RegisterView,
    TripAssignView,
    TripDetailView,
    TripListView,
    TripLogsView,
    TripPlanView,
    TripStatusView,
    TripViolationsView,
    VehicleAssignView,
    VehicleDetailView,
    VehicleListCreateView,
    VehicleUnassignView,
)

urlpatterns = [
    # Geocoding (must be before trips to avoid path conflicts)
    path("geocode/autocomplete/", GeocodeAutocompleteView.as_view(), name="geocode-autocomplete"),
    # Auth
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    # Invitations
    path("invitations/", InvitationListCreateView.as_view(), name="invitation-list-create"),
    path("invitations/validate/", InvitationValidateView.as_view(), name="invitation-validate"),
    path("invitations/accept/", InvitationAcceptView.as_view(), name="invitation-accept"),
    path("invitations/<uuid:pk>/", InvitationDetailView.as_view(), name="invitation-detail"),
    path("invitations/<uuid:pk>/revoke/", InvitationRevokeView.as_view(), name="invitation-revoke"),
    path("invitations/<uuid:pk>/resend/", InvitationResendView.as_view(), name="invitation-resend"),
    # Organization
    path("org/", OrganizationDetailView.as_view(), name="org-detail"),
    path("org/members/", MemberListView.as_view(), name="member-list"),
    path("org/members/<uuid:pk>/", MemberDetailView.as_view(), name="member-detail"),
    # Vehicles
    path("vehicles/", VehicleListCreateView.as_view(), name="vehicle-list-create"),
    path("vehicles/<uuid:pk>/", VehicleDetailView.as_view(), name="vehicle-detail"),
    path("vehicles/<uuid:pk>/assign/", VehicleAssignView.as_view(), name="vehicle-assign"),
    path("vehicles/<uuid:pk>/unassign/", VehicleUnassignView.as_view(), name="vehicle-unassign"),
    # Trips
    path("trips/plan/", TripPlanView.as_view(), name="trip-plan"),
    path("trips/", TripListView.as_view(), name="trip-list"),
    path("trips/<uuid:pk>/", TripDetailView.as_view(), name="trip-detail"),
    path("trips/<uuid:pk>/assign/", TripAssignView.as_view(), name="trip-assign"),
    path("trips/<uuid:pk>/logs/", TripLogsView.as_view(), name="trip-logs"),
    path("trips/<uuid:pk>/violations/", TripViolationsView.as_view(), name="trip-violations"),
    path("trips/<uuid:pk>/status/", TripStatusView.as_view(), name="trip-status"),
    # Profile
    path("profile/", ProfileView.as_view(), name="profile"),
]
