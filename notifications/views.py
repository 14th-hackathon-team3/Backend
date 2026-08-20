from django.shortcuts import render

# Create your views here.
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
 
from groups.models import Membership
from .models import Notification
from .serializers import NotificationSerializer
 
 
class NotificationListView(generics.ListAPIView):
    """
    GET /api/notifications/
    GET /api/notifications/?unread=true   -> 안읽은 것만
    로그인한 유저가 속한 모든 membership 기준으로 알림을 모아서 보여줌
    (한 유저가 여러 그룹에 속할 수 있으므로)
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
 
    def get_queryset(self):
        membership_ids = Membership.objects.filter(user=self.request.user).values_list("membership_id", flat=True)
        qs = Notification.objects.filter(membership_id__in=membership_ids)
 
        unread = self.request.query_params.get("unread")
        if unread == "true":
            qs = qs.filter(read_at__isnull=True)
        return qs
 
 
class NotificationReadView(APIView):
    """PATCH /api/notifications/<noti_id>/read/  -> 해당 알림 읽음 처리"""
    permission_classes = [permissions.IsAuthenticated]
 
    def patch(self, request, noti_id):
        membership_ids = Membership.objects.filter(user=request.user).values_list("membership_id", flat=True)
        notification = Notification.objects.filter(noti_id=noti_id, membership_id__in=membership_ids).first()
 
        if not notification:
            return Response({"detail": "알림을 찾을 수 없습니다."}, status=404)
 
        notification.mark_as_read()
        return Response(NotificationSerializer(notification).data, status=200)
 
 
class NotificationReadAllView(APIView):
    """PATCH /api/notifications/read-all/  -> 내 알림 전체 읽음 처리"""
    permission_classes = [permissions.IsAuthenticated]
 
    def patch(self, request):
        from django.utils import timezone
 
        membership_ids = Membership.objects.filter(user=request.user).values_list("membership_id", flat=True)
        updated = Notification.objects.filter(
            membership_id__in=membership_ids, read_at__isnull=True
        ).update(read_at=timezone.now())
 
        return Response({"updated_count": updated}, status=200)