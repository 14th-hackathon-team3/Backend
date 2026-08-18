from rest_framework import serializers
from .models import Episode, DailyLog, VoiceMemo, Todo

class EpisodeOnboardingSerializer(serializers.ModelSerializer):
    postpartum_week = serializers.ReadOnlyField()  # 계산값이라 읽기 전용으로만 응답에 포함

    class Meta:
        model = Episode
        fields = [
            'id',
            'delivery_type',
            'delivery_date',
            'discharge_date',
            'birth_order',
            'older_child_age',
            'initial_feeding_type',
            
            'recovery_location',
            'partner_referral_consent',
            'postpartum_week',
            'created_at',
            'initial_pain_areas', 
            'initial_pain_area_custom_text',
        ]
        read_only_fields = ['id', 'created_at']
        
    def validate(self, attrs):
        areas = attrs.get('initial_pain_areas', [])
        custom_text = attrs.get('initial_pain_area_custom_text', '')

        valid_values = [choice.value for choice in Episode.PainArea]
        for area in areas:
            if area not in valid_values:
                raise serializers.ValidationError(f"'{area}'는 유효하지 않은 통증 부위입니다.")

        # "특별한 통증 없음"은 다른 항목과 동시 선택 불가
        if Episode.PainArea.NONE in areas and len(areas) > 1:
            raise serializers.ValidationError("'특별한 통증 없음'은 다른 항목과 함께 선택할 수 없습니다.")

        # "직접 입력" 선택했으면 텍스트 필수
        if Episode.PainArea.CUSTOM in areas and not custom_text.strip():
            raise serializers.ValidationError("'직접 입력'을 선택했으면 통증 부위를 입력해주세요.")

        return attrs

    def validate_delivery_date(self, value):
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError("출산일은 미래일 수 없습니다.")
        return value
    
    
class DailyLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyLog
        fields = [
            'id', 'episode', 'log_date',
            'emotion', 'sleep_hours', 'pain_score', 'pain_area',
            'breastfeeding', 'medication', 'exercise', 'diet', 'memo',
            'skin_self_score', 'hair_loss_status',
            'skin_symptom_tags', 'pelvic_floor_symptoms',
            'created_at',
        ]
        read_only_fields = ['id', 'episode', 'created_at']

    def validate_pain_score(self, value):
        if value is not None and not (0 <= value <= 5):
            raise serializers.ValidationError("통증 점수는 5 사이여야 합니다.")
        return value

    def validate_skin_self_score(self, value):
        if value is not None and not (1 <= value <= 4):
            raise serializers.ValidationError("피부 자가평가는 1~4점 사이여야 합니다.")
        return value
    
class VoiceMemoSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceMemo
        fields = ['id', 'audio_file', 'duration_seconds', 'transcript_text', 'status', 'created_at']
        read_only_fields = ['id', 'transcript_text', 'status', 'created_at']
        
class TodoUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Todo
        fields = ['content']  # 산모가 고칠 수 있는 건 내용뿐, reason/assignee는 AI 판단 그대로 유지
            
class TodoSerializer(serializers.ModelSerializer):
    completed_by_name = serializers.SerializerMethodField()
    assignee_name = serializers.SerializerMethodField()

    class Meta:
        model = Todo
        fields = ['id', 'content', 'reason', 'is_skip', 'status', 'order_index',
                   'assignee_membership', 'assignee_name',
                   'completed_by', 'completed_by_name', 'completed_at', 'visibility']
        read_only_fields = ['id', 'reason', 'order_index', 'assignee_membership', 'assignee_name',
                             'completed_by', 'completed_by_name', 'completed_at']

    def get_completed_by_name(self, obj):
        return obj.completed_by.user.name if obj.completed_by else None  # User 모델 실제 필드명 확인 필요

    def get_assignee_name(self, obj):
        return obj.assignee_membership.user.name if obj.assignee_membership else None
      
class EpisodeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Episode
        fields = ['delivery_date', 'discharge_date']  # 산모가 실사용상 고칠 만한 값만 한정

    def validate_delivery_date(self, value):
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError("출산일은 미래일 수 없습니다.")
        return value