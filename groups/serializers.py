from rest_framework import serializers
from .models import Membership
 
 
class TimeSlotSerializer(serializers.Serializer):
    """available_time 리스트 안의 개별 항목 검증용"""
    DAY_CHOICES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
 
    day = serializers.ChoiceField(choices=DAY_CHOICES)
    start = serializers.TimeField()
    end = serializers.TimeField()
 
    def validate(self, attrs):
        if attrs["start"] >= attrs["end"]:
            raise serializers.ValidationError("start는 end보다 이전 시간이어야 합니다.")
        return attrs
 
 
class GuardianOnboardingSerializer(serializers.ModelSerializer):
    # available_time은 모델에서는 JSONField지만, 입력값 검증을 위해 여기서 직접 처리
    available_time = TimeSlotSerializer(many=True, required=False)
 
    class Meta:
        model = Membership
        fields = ["relation", "is_cohabiting", "available_time"]
 
    def validate_available_time(self, value):
        # TimeSlotSerializer가 OrderedDict를 돌려주는데 JSONField엔 datetime.time 객체가
        # 그대로 못 들어가니 문자열로 변환해서 저장
        return [
            {"day": slot["day"], "start": slot["start"].strftime("%H:%M"), "end": slot["end"].strftime("%H:%M")}
            for slot in value
        ]

class InviteCodeCheckSerializer(serializers.Serializer):
    """응답용 - 초대코드 검증 결과"""
    group_id = serializers.IntegerField()
    mother_name = serializers.CharField()
    is_valid = serializers.BooleanField()