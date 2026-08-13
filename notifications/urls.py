from django.urls import path
from .views import NotificationListView, NotificationReadView, NotificationReadAllView
 
urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("read-all/", NotificationReadAllView.as_view(), name="notification-read-all"),
    path("<int:noti_id>/read/", NotificationReadView.as_view(), name="notification-read"),
]