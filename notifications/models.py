from django.db import models

# Create your models here.

class Notification(models.Model):
    class NotiType(models.TextChoices):
        TODO_ASSIGNED = "todo_assigned", "할일 배정"
        DAILY_LOG_MISSING = "daily_log_missing", "일일기록 미작성"
        RECOVERY_PLAN_READY = "recovery_plan_ready", "회복플랜 생성됨"
        INVITE_JOINED = "invite_joined", "보호자 가입됨"
        # 필요한 만큼 추가
 
    noti_id = models.BigAutoField(primary_key=True)
    membership = models.ForeignKey(
        "groups.Membership",
        on_delete=models.CASCADE,
        db_column="membership_id",
        related_name="notifications",
    )
    type = models.CharField(max_length=50, choices=NotiType.choices)
    # 폴리모픽 참조: todos, daily_log 등 다양한 테이블을 가리킬 수 있어서
    # 진짜 FK 대신 문자열+id 조합으로 시작 (필요시 GenericForeignKey로 리팩터링)
    target_type = models.CharField(max_length=50, null=True, blank=True)
    target_id = models.BigIntegerField(null=True, blank=True)
    title = models.CharField(max_length=100)
    message = models.CharField(max_length=255)
    read_at = models.DateTimeField(null=True, blank=True)  # NULL=안읽음
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        db_table = "Notification"
        ordering = ["-created_at"]
 
    def __str__(self):
        return f"[{self.type}] {self.title}"
 
    def mark_as_read(self):
        if self.read_at is None:
            from django.utils import timezone
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])