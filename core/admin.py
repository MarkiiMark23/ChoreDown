from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Task, Behavior, Reward, RewardRedemption, PointTransaction, Notification


class TaskInline(admin.TabularInline):
    model = Task
    fk_name = 'assigned_to'
    extra = 0
    fields = ['title', 'status', 'points_value', 'points_earned', 'due_date', 'submitted_at', 'reviewed_at']
    readonly_fields = fields


class PointTransactionInline(admin.TabularInline):
    model = PointTransaction
    extra = 0
    fields = ['amount', 'transaction_type', 'description', 'created_at']
    readonly_fields = fields
    can_delete = False


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = [
        'username', 'first_name', 'email', 'is_parent', 'is_kid',
        'points', 'parent_account', 'notification_preference',
    ]
    list_filter = ['is_parent', 'is_kid', 'notification_preference', 'motivation_style', 'reminder_preference']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'preferred_name', 'parent_account__username']
    fieldsets = UserAdmin.fieldsets + (
        ('ChoreDown account', {
            'fields': (
                'is_parent', 'is_kid', 'points', 'parent_account', 'avatar_color',
                'notification_preference', 'preferred_name',
            )
        }),
        ('Kid support profile', {
            'fields': (
                'age_range', 'motivation_style', 'favorite_rewards', 'best_task_time',
                'reminder_preference', 'overwhelm_triggers', 'focus_supports',
                'sensory_notes', 'goals',
            )
        }),
        ('Parent preferences', {
            'fields': ('household_timezone', 'feedback_preferences', 'default_approval_note')
        }),
    )
    inlines = [TaskInline, PointTransactionInline]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'assigned_to', 'parent', 'status', 'category', 'priority',
        'points_value', 'points_earned', 'due_date', 'submitted_at', 'reviewed_at',
    ]
    list_filter = ['status', 'completed', 'category', 'priority', 'finished_late', 'not_quite', 'did_not_finish']
    search_fields = ['title', 'description', 'assigned_to__username', 'parent__username']
    readonly_fields = ['submitted_at', 'reviewed_at', 'completed_at']


@admin.register(Behavior)
class BehaviorAdmin(admin.ModelAdmin):
    list_display = ['associated_with', 'behavior_type', 'points_value', 'description', 'date_logged']
    list_filter = ['behavior_type']
    search_fields = ['description', 'associated_with__username', 'logged_by__username']


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ['title', 'points_cost', 'icon', 'is_active', 'parent']
    list_filter = ['is_active']
    search_fields = ['title', 'description', 'parent__username']


@admin.register(RewardRedemption)
class RewardRedemptionAdmin(admin.ModelAdmin):
    list_display = ['kid', 'reward', 'status', 'requested_at', 'resolved_at', 'resolved_by']
    list_filter = ['status']
    search_fields = ['kid__username', 'reward__title', 'reward__parent__username']


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'transaction_type', 'description', 'created_at']
    list_filter = ['transaction_type']
    search_fields = ['user__username', 'description']
    readonly_fields = ['created_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'recipient', 'actor', 'notification_type', 'title',
        'deliver_in_app', 'is_read', 'email_status', 'created_at',
    ]
    list_filter = ['notification_type', 'deliver_in_app', 'is_read', 'email_status']
    search_fields = ['recipient__username', 'actor__username', 'title', 'message']
    readonly_fields = ['created_at', 'read_at']
