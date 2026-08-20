from django.shortcuts import render, get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from .models import Episode, DailyLog, Todo, RecoveryPlan, VoiceMemo
from .serializers import EpisodeUpdateSerializer, EpisodeOnboardingSerializer, DailyLogSerializer, VoiceMemoSerializer, TodoUpdateSerializer, TodoSerializer
from groups.models import Membership
from datetime import date
from .services import upload_and_transcribe, generate_daily_plan, calculate_week_trend, get_episode_and_membership
from django.utils import timezone
from groups.models import Membership

class EpisodeOnboardingView(generics.CreateAPIView):
    #산모 온보딩 정보 저장 API (POST)
    serializer_class = EpisodeOnboardingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # 로그인한 유저를 자동으로 episode.user에 연결
        serializer.save(user=self.request.user)


class MyEpisodeView(generics.RetrieveUpdateAPIView):
    #현재 산모의 온보딩 정보 조회 API (GET)
    serializer_class = EpisodeOnboardingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        episode, _ = get_episode_and_membership(self.request.user)  # 수정
        return episode
    
    def get_serializer_class(self):
        return EpisodeUpdateSerializer if self.request.method in ("PUT", "PATCH") else EpisodeOnboardingSerializer

def get_active_episode(user):
    episode = Episode.objects.filter(user=user, is_active=True).order_by('-created_at').first()
    if not episode:
        raise NotFound("진행 중인 episode가 없습니다. 온보딩을 먼저 완료해주세요.")
    return episode

class DailyLogListCreateView(generics.ListCreateAPIView):
   
    serializer_class = DailyLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self): #최근 기록 목록 조회(최신순)
        episode, _ = get_episode_and_membership(self.request.user)
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
    
    
class VoiceMemoListCreateView(generics.ListCreateAPIView):
    serializer_class = VoiceMemoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        episode, _ = get_episode_and_membership(self.request.user)
        qs = VoiceMemo.objects.filter(daily_log__episode=episode).order_by('-created_at')
        log_date = self.request.query_params.get('log_date')
        daily_log_id = self.request.query_params.get('daily_log_id')
        if log_date:
            qs = qs.filter(daily_log__log_date=log_date)
        elif daily_log_id:
            qs = qs.filter(daily_log_id=daily_log_id)
        return qs

    def create(self, request, *args, **kwargs):
        episode = get_active_episode(request.user)  # 업로드는 산모 본인만
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response({"error": "audio 파일이 필요합니다."}, status=400)
        today_log, _ = DailyLog.objects.get_or_create(episode=episode, log_date=date.today())
        voice_memo = upload_and_transcribe(today_log, audio_file)
        serializer = self.get_serializer(voice_memo)
        return Response(serializer.data, status=201)
    
    
class VoiceMemoListView(generics.ListAPIView):
    """
    GET /api/care/voice-memos/?log_date=2026-08-20
    GET /api/care/voice-memos/?daily_log_id=12
    파라미터 없으면 전체(최신순) 반환
    """
    serializer_class = VoiceMemoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        episode, _ = get_episode_and_membership(self.request.user)
        qs = VoiceMemo.objects.filter(daily_log__episode=episode).order_by('-created_at')

        log_date = self.request.query_params.get('log_date')
        daily_log_id = self.request.query_params.get('daily_log_id')

        if log_date:
            qs = qs.filter(daily_log__log_date=log_date)
        elif daily_log_id:
            qs = qs.filter(daily_log_id=daily_log_id)

        return qs
    

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
    
class TodoUpdateView(generics.UpdateAPIView): # 지금 사용 X
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
        
class TodoDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET   /api/care/todos/<id>/   개별 todo 조회
    PATCH /api/care/todos/<id>/   개별 todo 수정 (content, is_skip 등)
    """
    serializer_class = TodoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        episode, membership = get_episode_and_membership(self.request.user)
        self.membership = membership
        return Todo.objects.filter(recovery_plan__episode=episode)
    
    def perform_update(self, serializer):
        # 필요하면 여기에 상태별 제약 추가
        serializer.save()

    def perform_destroy(self, instance):
        # 삭제는 산모(owner)만 가능하게 제한 — 보호자가 배정받은 할일을 임의로 지우지 못하게
        if self.membership.role != Membership.Role.OWNER:
            raise PermissionDenied("삭제는 산모만 가능합니다.")
        instance.delete()
    
class ConfirmAllTodosView(generics.GenericAPIView):# 혹시 몰라서 한 번에 확정 짓는 것도 만들어 놓음
    #지금 사용X
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
        episode, _ = get_episode_and_membership(request.user)
        return Response(calculate_week_trend(episode))
    
class TodayTodoListView(generics.GenericAPIView):
    """GET /api/care/todos/today/ - 산모/보호자 모두 조회 가능"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        episode, membership = get_episode_and_membership(request.user)
        plan = RecoveryPlan.objects.filter(episode=episode, plan_date=date.today()).first()

        if not plan:
            return Response({"mother_todos": [], "family_todos": [], "message": "오늘 생성된 플랜이 아직 없어요."})

        mother_qs = plan.todos.filter(assignee_membership__isnull=True)
        family_qs = plan.todos.filter(assignee_membership__isnull=False)

        # 보호자(role=member)는 산모가 '비공개' 설정한 항목을 볼 수 없음
        if membership.role != Membership.Role.OWNER:
            mother_qs = mother_qs.filter(visibility=Todo.Visibility.PUBLIC)
            family_qs = family_qs.filter(visibility=Todo.Visibility.PUBLIC)

        return Response({
            "plan_id": plan.pk,
            "bottleneck": plan.bottleneck,
            "mother_todos": TodoSerializer(mother_qs, many=True).data,
            "family_todos": TodoSerializer(family_qs, many=True).data,
            "my_role": membership.role,
        })
        
class TodoVisibilityToggleView(generics.GenericAPIView):
    """PATCH /api/care/todos/<id>/visibility/  body: {"visibility": "private"}"""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        episode, membership = get_episode_and_membership(request.user)

        # 비공개 설정은 산모(owner) 본인만 가능 — 보호자가 다른 항목을 숨길 순 없음
        if membership.role != Membership.Role.OWNER:
            return Response({"error": "비공개 설정은 산모만 변경할 수 있습니다."}, status=403)

        todo = get_object_or_404(Todo, pk=pk, recovery_plan__episode=episode)
        visibility = request.data.get('visibility')
        if visibility not in [Todo.Visibility.PUBLIC, Todo.Visibility.PRIVATE]:
            return Response({"error": "visibility는 public 또는 private이어야 합니다."}, status=400)

        todo.visibility = visibility
        todo.save(update_fields=['visibility'])
        return Response({"id": todo.pk, "visibility": todo.visibility})
    
class TodoCheckToggleView(generics.GenericAPIView):
    """POST /api/care/todos/<id>/check/ - 체크박스 토글 (완료 ↔ 완료취소)"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        episode, membership = get_episode_and_membership(request.user)
        todo = get_object_or_404(Todo, pk=pk, recovery_plan__episode=episode)

        if todo.completed_by_id == membership.pk:
            # 본인이 체크한 걸 다시 누르면 취소
            todo.completed_by = None
            todo.completed_at = None
        else:
            todo.completed_by = membership
            todo.completed_at = timezone.now()

        todo.save(update_fields=['completed_by', 'completed_at'])
        return Response(TodoSerializer(todo).data)
    
class TodayAnalysisView(generics.GenericAPIView):
    """GET /api/care/journey/today-analysis/ - 오늘의 AI 분석(요약/병목) 조회"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        episode, _ = get_episode_and_membership(request.user)
        plan = RecoveryPlan.objects.filter(episode=episode, plan_date=date.today()).first()

        if not plan:
            return Response({
                "has_plan": False,
                "message": "오늘의 분석이 아직 생성되지 않았어요.",
            })

        return Response({
            "has_plan": True,
            "plan_id": plan.pk,
            "plan_date": plan.plan_date,
            "ai_summary": plan.ai_summary,
            "bottleneck": plan.bottleneck,
            "reasoning": plan.reasoning,
            "tomorrow_goal": plan.tomorrow_goal,
        })