from django.urls import path
from .views import GuardianOnboardingView, InviteCodeCheckView, NotificationSettingView, GroupMemberListView, GroupMemberRemoveView
 
urlpatterns = [
    path("membership/onboarding/", GuardianOnboardingView.as_view(), name="guardian-onboarding"),
    path("membership/notification-settings/", NotificationSettingView.as_view(), name="notification-settings"),
    path("invite/<str:invite_code>/", InviteCodeCheckView.as_view(), name="invite-check"),
    path("members/", GroupMemberListView.as_view(), name="group-member-list"),
    path("members/<int:membership_id>/", GroupMemberRemoveView.as_view(), name="group-member-remove"),
]