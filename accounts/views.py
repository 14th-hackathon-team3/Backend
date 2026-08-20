from django.shortcuts import render

# Create your views here.
from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import SignupSerializer, CustomTokenObtainPairSerializer, UserSerializer, UserUpdateSerializer, LogoutSerializer, SocialLoginSerializer, ProfileImageUploadSerializer
from .models import User
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .services import SocialLoginService, SignupRequiredError, InvalidInviteCodeError
from .tokens import issue_tokens_for_user
from rest_framework.views import APIView

class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]
 
 
class LoginView(TokenObtainPairView):
    """POST { "email": ..., "password": ... } -> { access, refresh, user }"""
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]
 
 
class MeView(generics.RetrieveUpdateAPIView):
    """로그인한 본인 정보 확인용 (Authorization: Bearer <access> 헤더 필요)"""
    permission_classes = [permissions.IsAuthenticated]
 
    def get_object(self):
        return self.request.user
    def get_serializer_class(self):
        return UserUpdateSerializer if self.request.method in ("PUT", "PATCH") else UserSerializer

class LogoutView(generics.GenericAPIView):
    """POST { "refresh": "<refresh token>" } -> refresh token 블랙리스트 등록"""
    serializer_class = LogoutSerializer
    permission_classes = [permissions.IsAuthenticated]
 
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
        except TokenError:
            return Response({"detail": "유효하지 않은 토큰입니다."}, status=400)
        return Response(status=205)  # 205 Reset Content

class SocialLoginView(generics.GenericAPIView):
    serializer_class = SocialLoginSerializer
    permission_classes = [permissions.AllowAny]
 
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
 
        service = SocialLoginService(provider=data["provider"])
        try:
            user, is_new = service.login_or_signup(
                code=data["code"],
                user_type=data.get("user_type"),
                invite_code=data.get("invite_code"),
            )
        except SignupRequiredError:
            return Response(
                {"detail": "신규 유저입니다. user_type을 포함해 다시 요청해주세요.", "code": "SIGNUP_REQUIRED"},
                status=409,
            )
        except InvalidInviteCodeError as e:
            return Response({"detail": str(e), "code": "INVALID_INVITE_CODE"}, status=400)
 
        tokens = issue_tokens_for_user(user)
        return Response(
            {
                "is_new_user": is_new,
                "user": UserSerializer(user).data,
                **tokens,
            }
        )

class ProfileImageUploadView(generics.UpdateAPIView):
    """
    PATCH /api/accounts/me/photo/
    multipart/form-data로 profile_image 파일 전송
    """
    serializer_class = ProfileImageUploadSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
 
    def get_object(self):
        return self.request.user

class WithdrawView(APIView):
    """
    DELETE /api/accounts/me/
    soft delete: is_active=False로 비활성화.
    이후 로그인 시도 시 자동으로 막힘 (simplejwt가 is_active 체크함).
    """
    permission_classes = [permissions.IsAuthenticated]
 
    def delete(self, request):
        user = request.user
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(status=204)