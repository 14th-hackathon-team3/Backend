from django.urls import path
from .views import EpisodeOnboardingView, MyEpisodeView, DailyLogListCreateView, DailyLogDetailView, TodayLogView, VoiceMemoUploadView, GenerateDailyPlanView, TodoUpdateView, ConfirmDailyPlanView, TodoDetailView, ConfirmAllTodosView, WeekTrendView

urlpatterns = [
    path('onboarding/', EpisodeOnboardingView.as_view(), name='episode-onboarding'),
    path('me/', MyEpisodeView.as_view(), name='episode-me'),
    path('daily-logs/', DailyLogListCreateView.as_view(), name='daily-log-list-create'),
    path('daily-logs/today/', TodayLogView.as_view(), name='daily-log-today'),
    path('daily-logs/<int:pk>/', DailyLogDetailView.as_view(), name='daily-log-detail'),
    path('voice-memos/', VoiceMemoUploadView.as_view(), name='voice-memo-upload'),
    path('plans/generate/', GenerateDailyPlanView.as_view(), name='generate-daily-plan'),
    path('todos/<int:pk>/', TodoUpdateView.as_view(), name='todo-update'),
    path('plans/<int:plan_id>/confirm/', ConfirmDailyPlanView.as_view(), name='plan-confirm'),
    path('todos/<int:pk>/', TodoDetailView.as_view(), name='todo-detail'),
    path('plans/<int:plan_id>/confirm/', ConfirmAllTodosView.as_view(), name='confirm-all-todos'),
    path('journey/week-trend/', WeekTrendView.as_view(), name='week-trend'),
]
