from django.contrib import admin

# Register your models here.
from .models import Notification
 
 
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("noti_id", "membership", "type", "title", "read_at", "created_at")
    list_filter = ("type", "read_at")
    search_fields = ("title", "message")
 
 
admin.site.register(Notification, NotificationAdmin)