from django.urls import path
from .views import GuardianOnboardingView
 
urlpatterns = [
    path("membership/onboarding/", GuardianOnboardingView.as_view(), name="guardian-onboarding"),
]