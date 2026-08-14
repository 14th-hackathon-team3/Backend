from django.db import models

# Create your models here.
class PostpartumStage(models.Model):
    stage_id = models.BigAutoField(primary_key=True)
    stage_name = models.CharField(max_length=50)  # 예: "1~2주차"
    week_start = models.PositiveSmallIntegerField()
    week_end = models.PositiveSmallIntegerField()
    goal = models.CharField(max_length=255, null=True, blank=True)  # 예: "몸을 보호하고 회복 기반 만들기"
 
    class Meta:
        db_table = "postpartum_stages"
        ordering = ["week_start"]
 
    def __str__(self):
        return f"{self.stage_name} ({self.week_start}~{self.week_end}주)"