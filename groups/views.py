from django.shortcuts import render

# Create your views here.
from rest_framework import generics, permissions
from rest_framework.exceptions import NotFound
 
from .models import Membership
from .serializers import GuardianOnboardingSerializer
 
 
class GuardianOnboardingView(generics.UpdateAPIView):
    """
    PATCH /api/groups/membership/onboarding/
    로그인한 보호자의 가장 최근 membership(role=member)에
    relation / is_cohabiting / available_time을 채워넣는다.
    """
    serializer_class = GuardianOnboardingSerializer
    permission_classes = [permissions.IsAuthenticated]
 
    def get_object(self):
        membership = (
            Membership.objects
            .filter(user=self.request.user, role=Membership.Role.MEMBER)
            .order_by("-joined_at")
            .first()
        )
        if not membership:
            raise NotFound("보호자로 가입된 그룹이 없습니다.")
        return membership