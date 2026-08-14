from django.urls import path
from .views import PostpartumStageListView, CurrentStageView
 
urlpatterns = [
    path("stages/", PostpartumStageListView.as_view(), name="stage-list"),
    path("stages/current/", CurrentStageView.as_view(), name="stage-current"),
]