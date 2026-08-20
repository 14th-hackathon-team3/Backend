from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db import transaction as transaction 
from .models import User
from .services import create_group_membership_for_signup, InvalidInviteCodeError
 
class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    invite_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
 
    class Meta:
        model = User
        fields = ["user_id", "email", "name", "phone", "user_type", "password", "invite_code"]
        read_only_fields = ["user_id"]
 
    def validate(self, attrs):
        if attrs.get("user_type") == User.UserType.GUARDIAN and not attrs.get("invite_code"):
            raise serializers.ValidationError({"invite_code": "보호자 회원가입에는 초대코드가 필요합니다."})
        return attrs
 
    def create(self, validated_data):
        invite_code = validated_data.pop("invite_code", None)
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=validated_data["email"],
                    name=validated_data["name"],
                    user_type=validated_data["user_type"],
                    password=validated_data["password"],
                    phone=validated_data.get("phone"),
                )
                create_group_membership_for_signup(user, invite_code=invite_code)
        except InvalidInviteCodeError as e:
            raise serializers.ValidationError({"invite_code": str(e)})
        return user
 
 
class UserSerializer(serializers.ModelSerializer):
    """응답용 - 비밀번호 절대 노출 안 함"""
    class Meta:
        model = User
        fields = ["user_id", "email", "name", "phone", "user_type", "profile_image", "created_at"]
 
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["name", "phone"]   


class ProfileImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["profile_image"]

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