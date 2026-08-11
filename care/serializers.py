from rest_framework import serializers
from .models import Episode

class EpisodeOnboardingSerializer(serializers.ModelSerializer):
    postpartum_week = serializers.ReadOnlyField() 

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