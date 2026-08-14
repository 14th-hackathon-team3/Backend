from django.shortcuts import render
from django.db import transaction
from rest_framework import generics, permissions
from rest_framework.exceptions import NotFound, PermissionDenied
 
from .models import Membership, Group
from .serializers import GuardianOnboardingSerializer, InviteCodeCheckSerializer, NotificationSettingSerializer, GroupMemberSerializer
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
    
    def perform_update(self, serializer):
        # 동시 요청으로 3명 넘게 저장되는 것 방지 (락 걸고 처리)
        with transaction.atomic():
            group = serializer.instance.group
            Membership.objects.select_for_update().filter(group=group)  # 락 확보
            serializer.save()

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

class NotificationSettingView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/groups/membership/notification-settings/
    로그인한 유저의 membership 기준 알림 타입별 on/off 설정.
    (산모/보호자 둘 다 사용 가능 - role 구분 없음)
    """
    serializer_class = NotificationSettingSerializer
    permission_classes = [permissions.IsAuthenticated]
 
    def get_object(self):
        membership = (
            Membership.objects
            .filter(user=self.request.user)
            .order_by("-joined_at")
            .first()
        )
        if not membership:
            raise NotFound("가입된 그룹이 없습니다.")
        return membership

def get_my_group(user):
    """
    로그인한 유저(산모든 보호자든)가 속한 그룹을 반환.
    - 산모(role=owner)면 본인이 owner인 그룹
    - 보호자(role=member)면 본인이 속한 그룹
    가장 최근 membership 기준 1개.
    """
    membership = Membership.objects.filter(user=user).order_by("-joined_at").first()
    if not membership:
        raise NotFound("가입된 그룹이 없습니다.")
    return membership.group
 
 
class GroupMemberListView(generics.ListAPIView):
    """
    GET /api/groups/members/
    내 그룹에 속한 모든 멤버(산모+보호자) 목록.
    """
    serializer_class = GroupMemberSerializer
    permission_classes = [permissions.IsAuthenticated]
 
    def get_queryset(self):
        group = get_my_group(self.request.user)
        return Membership.objects.filter(group=group).select_related("user").order_by("-is_primary", "joined_at")
 
 
class GroupMemberRemoveView(generics.DestroyAPIView):
    """
    DELETE /api/groups/members/<membership_id>/
    산모(owner)만 그룹에서 특정 보호자를 제거할 수 있음.
    """
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "membership_id"
 
    def get_object(self):
        group = get_my_group(self.request.user)
 
        # 요청자가 owner인지 확인 (보호자는 강퇴 권한 없음)
        requester_membership = Membership.objects.filter(group=group, user=self.request.user).first()
        if not requester_membership or requester_membership.role != Membership.Role.OWNER:
            raise PermissionDenied("그룹 소유자만 멤버를 제거할 수 있습니다.")
 
        target = Membership.objects.filter(
            group=group, membership_id=self.kwargs["membership_id"]
        ).first()
        if not target:
            raise NotFound("해당 멤버를 찾을 수 없습니다.")
 
        # 본인(owner) 스스로는 강퇴 못 하게 방지
        if target.role == Membership.Role.OWNER:
            raise PermissionDenied("소유자 본인은 제거할 수 없습니다.")
 
        return target