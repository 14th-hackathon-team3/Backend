from django.urls import path
from .views import GuardianOnboardingView, InviteCodeCheckView, NotificationSettingView
 
urlpatterns = [
    path("membership/onboarding/", GuardianOnboardingView.as_view(), name="guardian-onboarding"),
    path("membership/notification-settings/", NotificationSettingView.as_view(), name="notification-settings"),
    path("invite/<str:invite_code>/", InviteCodeCheckView.as_view(), name="invite-check"),
]