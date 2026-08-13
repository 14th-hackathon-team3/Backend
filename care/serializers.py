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
            'initial_pain_area',
            'recovery_location',
            'partner_referral_consent',
            'postpartum_week',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

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
        if value is not None and not (0 <= value <= 10):
            raise serializers.ValidationError("통증 점수는 0~10 사이여야 합니다.")
        return value

    def validate_skin_self_score(self, value):
        if value is not None and not (1 <= value <= 5):
            raise serializers.ValidationError("피부 자가평가는 1~5점 사이여야 합니다.")
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
    class Meta:
        model = Todo
        fields = ['id', 'content', 'reason', 'is_skip', 'status', 'order_index',
                   'assignee_membership', 'completed_by', 'completed_at']
        read_only_fields = ['id', 'reason', 'order_index', 'assignee_membership', 'completed_by', 'completed_at']
        # content, is_skip, status만 산모가 수정 가능하게 열어둠