from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import CustomUser, Task, Behavior, Reward, RewardRedemption, PointTransaction, Notification


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'due_date', 'priority', 'category',
            'points_value', 'points_earned', 'status', 'completed', 'completed_at',
            'submitted_at', 'reviewed_at', 'parent_feedback', 'parent', 'assigned_to',
        ]
        read_only_fields = [
            'parent', 'points_earned', 'status', 'completed_at',
            'submitted_at', 'reviewed_at', 'parent_feedback',
        ]


class TaskCompleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            'fun_rating', 'time_taken', 'effort_note',
            'did_not_finish', 'finished_late', 'not_quite',
        ]


class BehaviorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Behavior
        fields = ['id', 'behavior_type', 'description', 'points_value', 'date_logged', 'logged_by', 'associated_with']
        read_only_fields = ['logged_by', 'date_logged']


class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = ['id', 'title', 'description', 'points_cost', 'icon', 'is_active', 'parent']
        read_only_fields = ['parent']


class RewardRedemptionSerializer(serializers.ModelSerializer):
    reward_title = serializers.CharField(source='reward.title', read_only=True)
    reward_icon = serializers.CharField(source='reward.icon', read_only=True)
    kid_username = serializers.CharField(source='kid.username', read_only=True)

    class Meta:
        model = RewardRedemption
        fields = [
            'id', 'kid', 'kid_username', 'reward', 'reward_title', 'reward_icon',
            'requested_at', 'status', 'resolved_at', 'resolved_by',
        ]
        read_only_fields = ['kid', 'requested_at', 'status', 'resolved_at', 'resolved_by']


class PointTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointTransaction
        fields = ['id', 'amount', 'transaction_type', 'description', 'created_at']
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'is_read',
            'task', 'reward_redemption', 'email_status', 'created_at', 'read_at',
        ]
        read_only_fields = fields


class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        # Public self-registration only ever creates a parent starting a new
        # family — matching the web /register/ flow. Roles are NOT client-settable
        # (otherwise anyone could mint orphan kids or arbitrary accounts via the API).
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_password(self, value):
        try:
            password_validation.validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def create(self, validated_data):
        user = CustomUser(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            is_parent=True,
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class KidSummarySerializer(serializers.ModelSerializer):
    pending_tasks = serializers.SerializerMethodField()
    completed_tasks = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'first_name', 'preferred_name', 'points',
            'avatar_color', 'pending_tasks', 'completed_tasks',
        ]

    def get_pending_tasks(self, obj):
        return obj.tasks.filter(status__in=['assigned', 'submitted', 'rejected']).count()

    def get_completed_tasks(self, obj):
        return obj.tasks.filter(status='approved').count()
