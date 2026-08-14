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
        
    class PainArea(models.TextChoices):
        PERINEUM = 'perineum', '회음부'
        LOWER_BACK = 'lower_back', '허리'
        PELVIS = 'pelvis', '골반'
        BREAST = 'breast', '가슴(유방)'
        WRIST = 'wrist', '손목'
        HEMORRHOID = 'hemorrhoid', '치질'
        NONE = 'none', '특별한 통증 없음'
        CUSTOM = 'custom', '직접 입력'

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
    
    recovery_location = models.CharField(max_length=100, blank=True)  
    partner_referral_consent = models.BooleanField(default=False) # 개인 정보 동의 필드
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    initial_pain_areas = models.JSONField(default=list, blank=True)  # JSON
    initial_pain_area_custom_text = models.CharField(max_length=100, blank=True)  # "직접 입력" 선택 시 텍스트

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

    class BreastMilkAmount(models.TextChoices):
        LOW = 'low', '적음'
        NORMAL = 'normal', '보통'
        HIGH = 'high', '많음'

    class HairLossStatus(models.TextChoices):
        SAME = 'same', '평소와 같음'
        SLIGHT = 'slight', '약간 빠짐'
        HEAVY = 'heavy', '많이 빠짐'
        
    class SkinConditionChoices(models.IntegerChoices):
        VERY_GOOD = 1, '매우 좋음'
        GOOD = 2, '좋음'
        MILD_TROUBLE = 3, '약간의 트러블'
        SEVERE_TROUBLE = 4, '트러블 심함'

    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name='daily_logs')
    log_date = models.DateField()

    emotion = models.CharField(max_length=15, choices=Emotion.choices, null=True, blank=True)
    sleep_hours = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    pain_score = models.PositiveSmallIntegerField(null=True, blank=True)
    pain_area = models.CharField(max_length=100, blank=True)
    breastfeeding = models.CharField(max_length=20, choices=Episode.FeedingType.choices, null=True, blank=True)
    medication = models.CharField(max_length=255, blank=True)
    exercise = models.CharField(max_length=255, blank=True)
    
    diet = models.JSONField(null=True, blank=True)  # {"breakfast": "...", "lunch": "...", "dinner": "..."}
    memo = models.TextField(blank=True)
    
    #활동량 수정
    activity_hours = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    activity_type = models.CharField(max_length=100, blank=True)

    #모유량 수정
    breast_milk_amount = models.CharField(max_length=10, choices=BreastMilkAmount.choices, null=True, blank=True)
    breastfeeding_pain_score = models.PositiveSmallIntegerField(null=True, blank=True)  # 1~5
    
    #피부 상태 척도 수정
    skin_self_score = models.PositiveSmallIntegerField(choices=SkinConditionChoices.choices, null=True, blank=True)

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
    
class RecoveryPlan(models.Model):
    class PlanType(models.TextChoices):
        DAILY = 'daily', '일간'

    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name='recovery_plans')
    plan_type = models.CharField(max_length=10, choices=PlanType.choices, default=PlanType.DAILY)
    plan_date = models.DateField()
    ai_summary = models.TextField(blank=True)        # 거시적 관점 2~3문장
    bottleneck = models.CharField(max_length=255, blank=True)   # 병목 한 줄
    reasoning = models.TextField(blank=True)          # 판단 근거 (버튼 눌러야 보이는 부분)
    tomorrow_goal = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['episode', 'plan_date'], name='unique_episode_plan_date')
        ]

    def __str__(self):
        return f"{self.episode} - {self.plan_date}"


class Todo(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', '임시생성'
        CONFIRMED = 'confirmed', '확정'
        DONE = 'done', '완료'

    class Visibility(models.TextChoices):
        PUBLIC = 'public', '공개'
        PRIVATE = 'private', '비공개'

    recovery_plan = models.ForeignKey(RecoveryPlan, on_delete=models.CASCADE, related_name='todos')
    content = models.CharField(max_length=255)
    reason = models.CharField(max_length=255, blank=True)   # 추천 이유 (버튼 눌러야 보임)
    is_skip = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    order_index = models.PositiveSmallIntegerField(default=0)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)

    # 산모용 todo는 None, 가족용 todo는 주 보호자 중 한 명이 배정됨
    assignee_membership = models.ForeignKey(
        'groups.Membership',  # 실제 앱 이름 확인
        on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_todos'
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        'groups.Membership', on_delete=models.SET_NULL, null=True, blank=True, related_name='completed_todos'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.content