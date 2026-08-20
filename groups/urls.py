from django.urls import path
from .views import PrimaryCaregiverToggleView, GuardianOnboardingView, InviteCodeCheckView, NotificationSettingView, GroupMemberListView, GroupMemberRemoveView, MyGroupView
urlpatterns = [
    path("membership/onboarding/", GuardianOnboardingView.as_view(), name="guardian-onboarding"),
    path("membership/notification-settings/", NotificationSettingView.as_view(), name="notification-settings"),
    path("invite/<str:invite_code>/", InviteCodeCheckView.as_view(), name="invite-check"),
    path("members/", GroupMemberListView.as_view(), name="group-member-list"),
    path("members/<int:membership_id>/", GroupMemberRemoveView.as_view(), name="group-member-remove"),
    path("members/<int:membership_id>/primary/", PrimaryCaregiverToggleView.as_view(), name="member-primary-toggle"),
    path("my-group/", MyGroupView.as_view(), name="my-group"),
]