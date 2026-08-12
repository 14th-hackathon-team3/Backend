from django.urls import path
from .views import GuardianOnboardingView, InviteCodeCheckView
 
urlpatterns = [
    path("membership/onboarding/", GuardianOnboardingView.as_view(), name="guardian-onboarding"),
    path("invite/<str:invite_code>/", InviteCodeCheckView.as_view(), name="invite-check"),
]