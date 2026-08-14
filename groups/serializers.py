from rest_framework import serializers
from .models import Membership
 
 
class GuardianOnboardingSerializer(serializers.ModelSerializer):
    AVAILABLE_TIME_CHOICES = ["morning", "afternoon", "evening", "night"]
    # morning: 06:00-12:00 / afternoon: 12:00-18:00 / evening: 18:00-22:00 / night: 22:00-06:00
 
    available_time = serializers.ListField(
        child=serializers.ChoiceField(choices=AVAILABLE_TIME_CHOICES),
        required=False,
        allow_empty=True,
    )
 
    class Meta:
        model = Membership
        fields = ["relation", "is_cohabiting", "available_time"]
 
    def validate_available_time(self, value):
        # 중복 제거 + 순서 고정 (프론트에서 뱃지 순서 일정하게 보이도록)
        order = self.AVAILABLE_TIME_CHOICES
        return [block for block in order if block in value]

class InviteCodeCheckSerializer(serializers.Serializer):
    """응답용 - 초대코드 검증 결과"""
    group_id = serializers.IntegerField()
    mother_name = serializers.CharField()
    is_valid = serializers.BooleanField()

class NotificationSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = [
            "notify_todo_created",
            "notify_family_todo_completed",
            "notify_family_todo_incomplete",
            "notify_own_todo_incomplete",
        ]