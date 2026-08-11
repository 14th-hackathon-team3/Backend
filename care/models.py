from django.db import models
from django.conf import settings
from datetime import date

class Episode(models.Model):
    class DeliveryType(models.TextChoices):
        NATURAL = 'natural', '자연분만'
        CESAREAN = 'cesarean', '제왕절개'

    class FeedingType(models.TextChoices):
        BREAST = 'breast', '모유'
        FORMULA = 'formula', '분유'
        MIXED = 'mixed', '혼합'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='episodes'
    )
    delivery_type = models.CharField(max_length=20, choices=DeliveryType.choices)
    delivery_date = models.DateField()
    discharge_date = models.DateField(null=True, blank=True)
    birth_order = models.PositiveSmallIntegerField(default=1)  
    older_child_age = models.PositiveSmallIntegerField(null=True, blank=True)
    initial_feeding_type = models.CharField(max_length=20, choices=FeedingType.choices)
    initial_pain_area = models.CharField(max_length=100, blank=True)
    recovery_location = models.CharField(max_length=100, blank=True)  
    partner_referral_consent = models.BooleanField(default=False) # 개인 정보 동의 필드
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def postpartum_week(self): #산후주차
        # 저장 안 하고 계산해서 내려줌 (매번 갱신 필요 없게)
        days = (date.today() - self.delivery_date).days
        return days // 7

    def __str__(self):
        return f"{self.user} - {self.delivery_date}"