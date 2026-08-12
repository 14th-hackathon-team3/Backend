from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Group, Membership
 
 
class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
 
 
class GroupAdmin(admin.ModelAdmin):
    list_display = ("group_id", "owner_user", "invite_code", "invite_code_expired_at", "created_at")
    search_fields = ("invite_code",)
    inlines = [MembershipInline]
 
 
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("membership_id", "user", "group", "role", "is_primary", "is_active", "joined_at")
    list_filter = ("role", "is_active", "is_primary")
 
 
admin.site.register(Group, GroupAdmin)
admin.site.register(Membership, MembershipAdmin)