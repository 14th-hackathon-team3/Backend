from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
 
from .models import User
 
 
class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
 
    class Meta:
        model = User
        fields = ["user_id", "email", "name", "phone", "user_type", "password"]
        read_only_fields = ["user_id"]
 
    def create(self, validated_data):
        # UserManager.create_user가 set_password까지 처리하므로
        # 반드시 이걸 통해서 생성해야 함 (그냥 User(**validated_data) 하면 비번 평문 저장됨)
        return User.objects.create_user(
            email=validated_data["email"],
            name=validated_data["name"],
            user_type=validated_data["user_type"],
            password=validated_data["password"],
            phone=validated_data.get("phone"),
        )
 
 
class UserSerializer(serializers.ModelSerializer):
    """응답용 - 비밀번호 절대 노출 안 함"""
    class Meta:
        model = User
        fields = ["user_id", "email", "name", "phone", "user_type", "created_at"]
 
 
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    simplejwt 기본 로그인 serializer 확장.
    USERNAME_FIELD가 email이라 기본 동작(email+password)은 그대로 두고,
    payload에 user_type만 추가하고 응답에 user 정보도 같이 내려줌.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["user_type"] = user.user_type
        return token
 
    def validate(self, attrs):
        data = super().validate(attrs)  # {"refresh": ..., "access": ...}
        data["user"] = UserSerializer(self.user).data
        return data

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

class SocialLoginSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=["kakao", "naver"])
    code = serializers.CharField()
    user_type = serializers.ChoiceField(choices=["mother", "guardian"], required=False)
    invite_code = serializers.CharField(required=False, allow_blank=True)