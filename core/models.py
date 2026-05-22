import secrets
import string as _string

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.utils import timezone

FAMILY_CODE_LENGTH = 6
# Excludes easily-confused characters (0/O, 1/I) so codes are easy to read aloud.
FAMILY_CODE_ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'


def generate_family_code():
    return ''.join(secrets.choice(FAMILY_CODE_ALPHABET) for _ in range(FAMILY_CODE_LENGTH))


class CustomUser(AbstractUser):
    NOTIFICATION_PREFERENCES = [
        ('in_app', 'In-app only'),
        ('email', 'Email only'),
        ('both', 'In-app and email'),
        ('none', 'No notifications'),
    ]
    MOTIVATION_CHOICES = [
        ('points', 'Points and progress'),
        ('praise', 'Praise and encouragement'),
        ('rewards', 'Rewards'),
        ('choice', 'Choice and independence'),
        ('quiet', 'Quiet completion'),
    ]
    REMINDER_CHOICES = [
        ('gentle', 'Gentle reminders'),
        ('visual', 'Visual checklist'),
        ('countdown', 'Countdown'),
        ('direct', 'Direct reminder'),
        ('none', 'No reminder preference'),
    ]

    is_parent = models.BooleanField(default=False)
    is_kid = models.BooleanField(default=False)
    points = models.PositiveIntegerField(default=0)
    parent_account = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='children'
    )
    avatar_color = models.CharField(max_length=7, default='#6C63FF')
    notification_preference = models.CharField(
        choices=NOTIFICATION_PREFERENCES,
        max_length=10,
        default='in_app',
    )
    preferred_name = models.CharField(max_length=80, blank=True)
    age_range = models.CharField(max_length=20, blank=True)
    motivation_style = models.CharField(choices=MOTIVATION_CHOICES, max_length=20, blank=True)
    favorite_rewards = models.TextField(blank=True)
    best_task_time = models.CharField(max_length=80, blank=True)
    reminder_preference = models.CharField(choices=REMINDER_CHOICES, max_length=20, blank=True)
    overwhelm_triggers = models.TextField(blank=True)
    focus_supports = models.TextField(blank=True)
    sensory_notes = models.TextField(blank=True)
    goals = models.TextField(blank=True)
    household_timezone = models.CharField(max_length=64, blank=True)
    feedback_preferences = models.TextField(blank=True)
    default_approval_note = models.TextField(blank=True)
    family_code = models.CharField(max_length=FAMILY_CODE_LENGTH, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.family_code:
            code = generate_family_code()
            while CustomUser.objects.filter(family_code=code).exists():
                code = generate_family_code()
            self.family_code = code
        super().save(*args, **kwargs)

    def clean(self):
        if self.is_parent and self.is_kid:
            raise ValidationError("A user cannot be both a parent and a kid.")

    def is_parent_user(self):
        return self.is_parent

    def is_kid_user(self):
        return self.is_kid

    @property
    def family_head(self):
        """The primary parent of this user's family (self if there's no parent_account)."""
        return self.parent_account if self.parent_account_id else self

    @property
    def family_join_code(self):
        """The single shareable code for the whole family (always the head's)."""
        return self.family_head.family_code

    def family_parent_ids(self):
        """IDs of every parent in this family (the head plus any co-parents who joined)."""
        head = self.family_head
        ids = {head.id}
        ids.update(
            head.children.filter(is_parent=True).values_list('id', flat=True)
        )
        return ids

    def family_kids(self):
        """All kids belonging to this user's family, regardless of which parent added them."""
        return CustomUser.objects.filter(parent_account=self.family_head, is_kid=True)

    def __str__(self):
        role = 'Parent' if self.is_parent else 'Kid'
        return f"{self.username} ({role})"


class Task(models.Model):
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('submitted', 'Submitted for Review'),
        ('approved', 'Approved'),
        ('rejected', 'Needs Adjustments'),
    ]
    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Urgent'),
    ]
    CATEGORY_CHOICES = [
        ('chores', 'Chores'),
        ('homework', 'Homework'),
        ('hygiene', 'Hygiene'),
        ('outdoor', 'Outdoor'),
        ('other', 'Other'),
    ]
    FUN_RATING_CHOICES = [
        (1, 'Terrible'),
        (2, 'Not Great'),
        (3, 'Okay'),
        (4, 'Fun'),
        (5, 'Amazing!'),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=20, default='chores')
    points_value = models.PositiveIntegerField(default=10)
    points_earned = models.IntegerField(null=True, blank=True)
    status = models.CharField(choices=STATUS_CHOICES, max_length=12, default='assigned')
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_tasks',
    )
    fun_rating = models.IntegerField(choices=FUN_RATING_CHOICES, null=True, blank=True)
    time_taken = models.DurationField(null=True, blank=True)
    effort_note = models.TextField(blank=True)
    parent_feedback = models.TextField(blank=True)
    did_not_finish = models.BooleanField(default=False)
    finished_late = models.BooleanField(default=False)
    not_quite = models.BooleanField(default=False)
    parent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assigned_tasks')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks')

    def __str__(self):
        return f"{self.title} — {self.get_status_display()}"

    @property
    def actual_points_label(self):
        if self.points_earned is None:
            return 'Waiting for parent'
        sign = '+' if self.points_earned > 0 else ''
        return f'{sign}{self.points_earned} pts'


class Behavior(models.Model):
    BEHAVIOR_TYPES = [
        ('positive', 'Positive'),
        ('negative', 'Negative'),
    ]

    behavior_type = models.CharField(choices=BEHAVIOR_TYPES, max_length=10)
    description = models.TextField()
    points_value = models.PositiveIntegerField(default=5)
    date_logged = models.DateTimeField(auto_now_add=True)
    logged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='logged_behaviors')
    associated_with = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='behaviors')

    def __str__(self):
        return f"{self.get_behavior_type_display()} — {self.associated_with.username}"


class Reward(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    points_cost = models.PositiveIntegerField()
    icon = models.CharField(max_length=10, default='🎁')
    is_active = models.BooleanField(default=True)
    parent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rewards')

    def __str__(self):
        return f"{self.icon} {self.title} ({self.points_cost} pts)"


class RewardRedemption(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Not This Time'),
    ]

    kid = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='redemptions')
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE, related_name='redemptions')
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(choices=STATUS_CHOICES, max_length=10, default='pending')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='resolved_redemptions'
    )

    def __str__(self):
        return f"{self.kid.username} → {self.reward.title} ({self.status})"


class PointTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('task', 'Task Completion'),
        ('behavior_positive', 'Positive Behavior'),
        ('behavior_negative', 'Negative Behavior'),
        ('redemption', 'Reward Redeemed'),
        ('bonus', 'Bonus Points'),
        ('penalty', 'Penalty'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='point_transactions')
    amount = models.IntegerField()
    transaction_type = models.CharField(choices=TRANSACTION_TYPES, max_length=20)
    description = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.amount >= 0 else ''
        return f"{self.user.username}: {sign}{self.amount} ({self.get_transaction_type_display()})"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('task_submitted', 'Task Submitted'),
        ('task_approved', 'Task Approved'),
        ('task_rejected', 'Task Needs Adjustments'),
        ('reward_requested', 'Reward Requested'),
        ('reward_approved', 'Reward Approved'),
        ('reward_denied', 'Reward Not This Time'),
        ('points_changed', 'Points Changed'),
        ('system', 'System'),
    ]
    EMAIL_STATUSES = [
        ('not_requested', 'Not requested'),
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('skipped', 'Skipped'),
        ('failed', 'Failed'),
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sent_notifications',
    )
    notification_type = models.CharField(choices=NOTIFICATION_TYPES, max_length=30)
    title = models.CharField(max_length=120)
    message = models.TextField()
    deliver_in_app = models.BooleanField(default=True)
    is_read = models.BooleanField(default=False)
    task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.CASCADE, related_name='notifications')
    reward_redemption = models.ForeignKey(
        RewardRedemption,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    email_status = models.CharField(choices=EMAIL_STATUSES, max_length=20, default='not_requested')
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.username}: {self.title}"
