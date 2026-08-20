from django.contrib import admin

# Register your models here.
from .models import PostpartumStage
 
 
class PostpartumStageAdmin(admin.ModelAdmin):
    list_display = ("stage_id", "stage_name", "week_start", "week_end", "goal")
    ordering = ("week_start",)
 
 
admin.site.register(PostpartumStage, PostpartumStageAdmin)