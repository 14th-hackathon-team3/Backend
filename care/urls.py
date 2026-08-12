from django.urls import path
from .views import EpisodeOnboardingView, MyEpisodeView, DailyLogListCreateView, DailyLogDetailView, TodayLogView, VoiceMemoUploadView

urlpatterns = [
    path('onboarding/', EpisodeOnboardingView.as_view(), name='episode-onboarding'),
    path('me/', MyEpisodeView.as_view(), name='episode-me'),
    path('daily-logs/', DailyLogListCreateView.as_view(), name='daily-log-list-create'),
    path('daily-logs/today/', TodayLogView.as_view(), name='daily-log-today'),
    path('daily-logs/<int:pk>/', DailyLogDetailView.as_view(), name='daily-log-detail'),
    path('voice-memos/', VoiceMemoUploadView.as_view(), name='voice-memo-upload'),
]
