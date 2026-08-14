from django.shortcuts import render

# Create your views here.
from rest_framework import generics, permissions
from rest_framework.exceptions import NotFound, ValidationError
from .models import PostpartumStage
from .serializers import PostpartumStageSerializer
 
 
class PostpartumStageListView(generics.ListAPIView):
    """
    GET /api/content/stages/
    전체 산후단계 목록 (참고용 콘텐츠라 로그인 없이도 조회 가능)
    """
    queryset = PostpartumStage.objects.all()
    serializer_class = PostpartumStageSerializer
    permission_classes = [permissions.AllowAny]
 
 
class CurrentStageView(generics.RetrieveAPIView):
    """
    GET /api/content/stages/current/?week=5
    특정 경과주차가 속하는 단계 1개 조회.
    (프론트/다른 앱이 episode.postpartum_week 값을 여기 넘겨서 사용)
    """
    serializer_class = PostpartumStageSerializer
    permission_classes = [permissions.AllowAny]
 
    def get_object(self):
        week = self.request.query_params.get("week")
        if week is None:
            raise ValidationError({"week": "week 쿼리 파라미터가 필요합니다."})
        try:
            week = int(week)
        except ValueError:
            raise ValidationError({"week": "week는 정수여야 합니다."})
 
        stage = PostpartumStage.objects.filter(week_start__lte=week, week_end__gte=week).first()
        if not stage:
            raise NotFound(f"{week}주차에 해당하는 산후단계를 찾을 수 없습니다.")
        return stage