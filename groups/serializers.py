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
        fields = ["relation", "is_cohabiting", "is_primary",  "available_time"]
 
    def validate_available_time(self, value):
        # TimeSlotSerializer가 OrderedDict를 돌려주는데 JSONField엔 datetime.time 객체가
        # 그대로 못 들어가니 문자열로 변환해서 저장
        return [
            {"day": slot["day"], "start": slot["start"].strftime("%H:%M"), "end": slot["end"].strftime("%H:%M")}
            for slot in value
        ]
    def validate_is_primary(self, value):
        # False로 보내거나 안 보내면 체크할 필요 없음
        if not value:
            return value

        instance = self.instance  # UpdateAPIView라 항상 존재
        primary_count = (
            Membership.objects
            .filter(group=instance.group, role=Membership.Role.MEMBER, is_primary=True)
            .exclude(pk=instance.pk)  # 본인 제외하고 세기
            .count()
        )
        if primary_count >= 3:
            raise serializers.ValidationError("주 보호자는 그룹당 최대 3명까지 지정할 수 있습니다.")
        return value