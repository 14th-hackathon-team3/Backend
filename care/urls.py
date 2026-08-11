from django.urls import path
from .views import EpisodeOnboardingView, MyEpisodeView

urlpatterns = [
    path('onboarding/', EpisodeOnboardingView.as_view(), name='episode-onboarding'),
    path('me/', MyEpisodeView.as_view(), name='episode-me'),
]