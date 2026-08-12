from django.shortcuts import render

# Create your views here.
from rest_framework import generics, permissions
from rest_framework.exceptions import NotFound
 
from .models import Membership, Group
from .serializers import GuardianOnboardingSerializer, InviteCodeCheckSerializer
 
from rest_framework.views import APIView
from rest_framework.response import Response

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

class InviteCodeCheckView(APIView):
    """
    GET /api/groups/invite/<invite_code>/
    가입 전(비회원 포함) 초대코드가 유효한지 미리 확인하는 용도.
    """
    permission_classes = [permissions.AllowAny]
 
    def get(self, request, invite_code):
        group = Group.objects.select_related("owner_user").filter(invite_code=invite_code).first()
 
        if not group:
            return Response(
                {"detail": "존재하지 않는 초대코드입니다.", "code": "NOT_FOUND"},
                status=404,
            )
 
        if not group.is_invite_code_valid():
            return Response(
                {"detail": "만료된 초대코드입니다.", "code": "EXPIRED"},
                status=400,
            )
 
        # 로그인한 상태로 조회했다면, 이미 가입된 그룹인지도 같이 알려줌
        already_joined = False
        if request.user and request.user.is_authenticated:
            already_joined = Membership.objects.filter(group=group, user=request.user).exists()
 
        serializer = InviteCodeCheckSerializer({
            "group_id": group.group_id,
            "mother_name": group.owner_user.name,
            "is_valid": True,
        })
        data = serializer.data
        data["already_joined"] = already_joined
        return Response(data, status=200)