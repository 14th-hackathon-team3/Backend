from django.db import models

# Create your models here.
import random
import string
from datetime import timedelta
 
from django.conf import settings
from django.db import models
from django.utils import timezone
 
 
def generate_invite_code(length=8):
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))
 
 
class Group(models.Model):
    group_id = models.BigAutoField(primary_key=True)
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column="owner_user_id",
        related_name="owned_groups",
    )
    invite_code = models.CharField(max_length=20, unique=True, default=generate_invite_code)
    invite_code_expired_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        db_table = "group"
 
    def __str__(self):
        return f"Group {self.group_id} (owner: {self.owner_user_id})"
 
    def is_invite_code_valid(self):
        return timezone.now() < self.invite_code_expired_at
 
    def reissue_invite_code(self, valid_hours=48):
        self.invite_code = generate_invite_code()
        self.invite_code_expired_at = timezone.now() + timedelta(hours=valid_hours)
        self.save(update_fields=["invite_code", "invite_code_expired_at"])
 
 
class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "산모(소유자)"
        MEMBER = "member", "보호자"
 
    class DataScope(models.TextChoices):
        FULL = "full", "전체 조회"
        PARTIAL = "partial", "일부 조회"
 
    class NotificationFrequency(models.TextChoices):
        DAILY = "daily", "매일"
        EVERY_OTHER_DAY = "every_other_day", "격일"
        OFF = "off", "안 받음"
 
    membership_id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, db_column="group_id", related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="memberships",
    )
 
    role = models.CharField(max_length=10, choices=Role.choices)
    # 실제 관계(남편/부모님/도우미 등) - UI 표시용, 권한 로직에는 사용 안 함
    relation = models.CharField(max_length=20, null=True, blank=True)
    data_scope = models.CharField(max_length=20, choices=DataScope.choices, default=DataScope.FULL)
    notification_frequency = models.CharField(
        max_length=20, choices=NotificationFrequency.choices, default=NotificationFrequency.DAILY
    )
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)  # 주보호자 여부
    is_cohabiting = models.BooleanField(default=False)
    available_time = models.JSONField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        db_table = "membership"
        unique_together = ("group", "user")  # 같은 그룹 중복가입 방지
 
    def __str__(self):
        return f"{self.user_id} - group {self.group_id} ({self.role})"