from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.utils import timezone


class CustomUser(AbstractUser):
    is_parent = models.BooleanField(default=False)
    is_kid = models.BooleanField(default=False)
    points = models.PositiveIntegerField(default=0)
    parent_account = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='children'
    )
    avatar_color = models.CharField(max_length=7, default='#6C63FF')

    def clean(self):
        if self.is_parent and self.is_kid:
            raise ValidationError("A user cannot be both a parent and a kid.")

    def is_parent_user(self):
        return self.is_parent

    def is_kid_user(self):
        return self.is_kid

    def __str__(self):
        role = 'Parent' if self.is_parent else 'Kid'
        return f"{self.username} ({role})"


class Task(models.Model):
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
    due_date = models.DateTimeField()
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=20, default='chores')
    points_value = models.PositiveIntegerField(default=10)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    fun_rating = models.IntegerField(choices=FUN_RATING_CHOICES, null=True, blank=True)
    time_taken = models.DurationField(null=True, blank=True)
    did_not_finish = models.BooleanField(default=False)
    finished_late = models.BooleanField(default=False)
    not_quite = models.BooleanField(default=False)
    parent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assigned_tasks')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks')

    def __str__(self):
        return f"{self.title} — {'Done' if self.completed else 'Pending'}"


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
        ('denied', 'Denied'),
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
