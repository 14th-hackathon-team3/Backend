from django.shortcuts import render, get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from .models import Episode, DailyLog, Todo, RecoveryPlan
from .serializers import EpisodeOnboardingSerializer, DailyLogSerializer, VoiceMemoSerializer, TodoUpdateSerializer, TodoSerializer
from datetime import date
from .services import upload_and_transcribe, generate_daily_plan, calculate_week_trend

class EpisodeOnboardingView(generics.CreateAPIView):
    #산모 온보딩 정보 저장 API (POST)
    serializer_class = EpisodeOnboardingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # 로그인한 유저를 자동으로 episode.user에 연결
        serializer.save(user=self.request.user)


class MyEpisodeView(generics.RetrieveAPIView):
    #현재 산모의 온보딩 정보 조회 API (GET)
    serializer_class = EpisodeOnboardingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return Episode.objects.filter(user=self.request.user, is_active=True).latest('created_at')


def get_active_episode(user):
    episode = Episode.objects.filter(user=user, is_active=True).order_by('-created_at').first()
    if not episode:
        raise NotFound("진행 중인 episode가 없습니다. 온보딩을 먼저 완료해주세요.")
    return episode

class DailyLogListCreateView(generics.ListCreateAPIView):
   
    serializer_class = DailyLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self): #최근 기록 목록 조회(최신순)
        episode = get_active_episode(self.request.user)
        queryset = DailyLog.objects.filter(episode=episode)

        # ?days=7 쿼리파라미터로 최근 N일만 조회 가능하게
        days = self.request.query_params.get('days')
        if days:
            queryset = queryset[:int(days)]
        return queryset

    def create(self, request, *args, **kwargs):
        episode = get_active_episode(request.user)
        log_date = request.data.get('log_date', date.today().isoformat())

        # 오늘 기록이 이미 있으면 update, 없으면 create
        instance, created = DailyLog.objects.get_or_create(
            episode=episode,
            log_date=log_date,
        )
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(episode=episode)

        status_code = 201 if created else 200
        return Response(serializer.data, status=status_code)
    
class DailyLogDetailView(generics.RetrieveUpdateAPIView):
   
    serializer_class = DailyLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        episode = get_active_episode(self.request.user)
        return DailyLog.objects.filter(episode=episode)
    
    
class VoiceMemoUploadView(generics.GenericAPIView):
    """POST /api/care/voice-memos/  (multipart/form-data, key='audio')"""
    serializer_class = VoiceMemoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        episode = get_active_episode(request.user)
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response({"error": "audio 파일이 필요합니다."}, status=400)

        today_log, _ = DailyLog.objects.get_or_create(
            episode=episode, log_date=date.today()
        )

        voice_memo = upload_and_transcribe(today_log, audio_file)
        serializer = self.get_serializer(voice_memo)
        return Response(serializer.data, status=201)
    
class GenerateDailyPlanView(generics.GenericAPIView):
    """POST /api/care/plans/generate/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        episode = get_active_episode(request.user)
        try:
            plan = generate_daily_plan(episode)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

        return Response({
            "plan_id": plan.pk,
            "ai_summary": plan.ai_summary,
            "bottleneck": plan.bottleneck,
            "reasoning": plan.reasoning,
            "tomorrow_goal": plan.tomorrow_goal,
            "mother_todos": [
                {"id": t.pk, "content": t.content, "reason": t.reason}
                for t in plan.todos.filter(assignee_membership__isnull=True)
            ],
            "family_todos": [
                {"id": t.pk, "content": t.content, "reason": t.reason, "assignee_membership_id": t.assignee_membership_id}
                for t in plan.todos.filter(assignee_membership__isnull=False)
            ],
        }, status=201)
        
class TodayLogView(generics.RetrieveAPIView):
    
    serializer_class = DailyLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        episode = get_active_episode(self.request.user)
        log = DailyLog.objects.filter(episode=episode, log_date=date.today()).first()
        if not log:
            raise NotFound("오늘 기록이 아직 없습니다.")
        return log
    
class TodoUpdateView(generics.UpdateAPIView):
    """PATCH /api/care/todos/<id>/  — draft 상태일 때만 산모가 내용 수정"""
    serializer_class = TodoUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Todo.objects.filter(recovery_plan__episode__user=self.request.user)

    def get_object(self):
        todo = super().get_object()
        if todo.status != Todo.Status.DRAFT:
            raise PermissionDenied("이미 확정된 할 일은 수정할 수 없습니다.")
        return todo
    

class ConfirmDailyPlanView(generics.GenericAPIView):
    """POST /api/care/plans/<plan_id>/confirm/ — 오늘 draft todos를 한 번에 확정"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, plan_id):
        plan = get_object_or_404(RecoveryPlan, pk=plan_id, episode__user=request.user)
        updated = plan.todos.filter(status=Todo.Status.DRAFT).update(status=Todo.Status.CONFIRMED)

        if updated == 0:
            return Response({"error": "확정할 draft 상태의 할 일이 없습니다."}, status=400)

        return Response({
            "plan_id": plan.pk,
            "confirmed_count": updated,
        }, status=200)
        
class TodoDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/care/todos/<id>/   개별 todo 조회
    PATCH /api/care/todos/<id>/   개별 todo 수정 (content, is_skip 등)
    """
    serializer_class = TodoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 본인 episode에 속한 todo만 수정 가능하게 제한
        episode = get_active_episode(self.request.user)
        return Todo.objects.filter(recovery_plan__episode=episode)
    
class ConfirmAllTodosView(generics.GenericAPIView):# 혹시 몰라서 한 번에 확정 짓는 것도 만들어 놓음
    """POST /api/care/plans/<plan_id>/confirm/  - 오늘 플랜의 모든 draft todo를 한번에 확정"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, plan_id):
        episode = get_active_episode(request.user)
        updated = Todo.objects.filter(
            recovery_plan_id=plan_id,
            recovery_plan__episode=episode,
            status=Todo.Status.DRAFT
        ).update(status=Todo.Status.CONFIRMED)
        return Response({"confirmed_count": updated})
    
class WeekTrendView(generics.GenericAPIView):
    """GET /api/care/journey/week-trend/"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        episode = get_active_episode(request.user)
        return Response(calculate_week_trend(episode))