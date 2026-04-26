from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Task, Behavior, Reward, RewardRedemption, PointTransaction


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'first_name', 'email', 'is_parent', 'is_kid', 'points', 'parent_account']
    list_filter = ['is_parent', 'is_kid']
    fieldsets = UserAdmin.fieldsets + (
        ('TaskDown', {'fields': ('is_parent', 'is_kid', 'points', 'parent_account', 'avatar_color')}),
    )


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'assigned_to', 'parent', 'category', 'priority', 'points_value', 'completed', 'due_date']
    list_filter = ['completed', 'category', 'priority']
    search_fields = ['title', 'assigned_to__username']


@admin.register(Behavior)
class BehaviorAdmin(admin.ModelAdmin):
    list_display = ['associated_with', 'behavior_type', 'points_value', 'description', 'date_logged']
    list_filter = ['behavior_type']


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ['title', 'points_cost', 'icon', 'is_active', 'parent']
    list_filter = ['is_active']


@admin.register(RewardRedemption)
class RewardRedemptionAdmin(admin.ModelAdmin):
    list_display = ['kid', 'reward', 'status', 'requested_at', 'resolved_at']
    list_filter = ['status']


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'transaction_type', 'description', 'created_at']
    list_filter = ['transaction_type']
