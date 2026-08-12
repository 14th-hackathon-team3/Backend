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
    
    
class DailyLog(models.Model):
    class Emotion(models.TextChoices):
        HAPPY = 'happy', '행복한'
        ANGRY = 'angry', '화남'
        LOW_ENERGY = 'low_energy', '에너지부족'
        SAD = 'sad', '슬픈'
        DEPRESSED = 'depressed', '우울한'
        CONFUSED = 'confused', '혼란스러운'
        CALM = 'calm', '차분한'
        MOODY = 'moody', '변덕스러운'
        IRRITATED = 'irritated', '짜증나는'
        WORRIED = 'worried', '걱정스러운'
        ACTIVE = 'active', '활동적인'

    class ActivityLevel(models.TextChoices):
        LOW = 'low', '낮음'
        NORMAL = 'normal', '보통'
        HIGH = 'high', '많음'

    class HairLossStatus(models.TextChoices):
        SAME = 'same', '평소와 같음'
        SLIGHT = 'slight', '약간 빠짐'
        HEAVY = 'heavy', '많이 빠짐'

    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name='daily_logs')
    log_date = models.DateField()

    emotion = models.CharField(max_length=15, choices=Emotion.choices, null=True, blank=True)
    sleep_hours = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    pain_score = models.PositiveSmallIntegerField(null=True, blank=True)
    pain_area = models.CharField(max_length=100, blank=True)
    breastfeeding = models.CharField(max_length=20, choices=Episode.FeedingType.choices, null=True, blank=True)
    medication = models.CharField(max_length=255, blank=True)
    exercise = models.CharField(max_length=255, blank=True)
    activity_level = models.CharField(max_length=10, choices=ActivityLevel.choices, null=True, blank=True)
    diet = models.JSONField(null=True, blank=True)  # {"breakfast": "...", "lunch": "...", "dinner": "..."}
    memo = models.TextField(blank=True)

    skin_self_score = models.PositiveSmallIntegerField(null=True, blank=True)
    hair_loss_status = models.CharField(max_length=20, choices=HairLossStatus.choices, null=True, blank=True)
    skin_symptom_tags = models.JSONField(null=True, blank=True)
    pelvic_floor_symptoms = models.JSONField(null=True, blank=True)

    private_fields = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['episode', 'log_date'], name='unique_episode_log_date')
        ]
        ordering = ['-log_date']

    def __str__(self):
        return f"{self.episode} - {self.log_date}"
    
    
class VoiceMemo(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', '처리중'
        DONE = 'done', '완료'
        FAILED = 'failed', '실패'

    daily_log = models.ForeignKey(DailyLog, on_delete=models.CASCADE, related_name='voice_memos')
    audio_file = models.FileField(upload_to='voice_memos/%Y/%m/%d/')
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    transcript_text = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.daily_log} - voice memo"