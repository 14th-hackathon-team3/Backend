from rest_framework import serializers
from .models import PostpartumStage
 
 
class PostpartumStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostpartumStage
        fields = ["stage_id", "stage_name", "week_start", "week_end", "goal"]