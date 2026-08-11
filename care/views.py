from django.shortcuts import render
from rest_framework import generics, permissions
from .models import Episode
from .serializers import EpisodeOnboardingSerializer

class EpisodeOnboardingView(generics.CreateAPIView):
    """산모 온보딩 정보 저장 API (POST)"""
    serializer_class = EpisodeOnboardingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # 로그인한 유저를 자동으로 episode.user에 연결
        serializer.save(user=self.request.user)


class MyEpisodeView(generics.RetrieveAPIView):
    """현재 산모의 온보딩 정보 조회 API (GET)"""
    serializer_class = EpisodeOnboardingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return Episode.objects.filter(user=self.request.user, is_active=True).latest('created_at')
