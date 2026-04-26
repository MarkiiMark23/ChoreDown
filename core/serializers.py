from rest_framework import serializers
from .models import CustomUser, Task, Behavior, Reward, RewardRedemption, PointTransaction


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'due_date', 'priority', 'category',
            'points_value', 'completed', 'completed_at', 'parent', 'assigned_to',
        ]
        read_only_fields = ['parent', 'completed_at']


class TaskCompleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['completed', 'fun_rating', 'time_taken', 'did_not_finish', 'finished_late', 'not_quite']


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


class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'is_parent', 'is_kid']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        if data.get('is_parent') and data.get('is_kid'):
            raise serializers.ValidationError("A user cannot be both a parent and a kid.")
        return data

    def create(self, validated_data):
        user = CustomUser(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            is_parent=validated_data.get('is_parent', False),
            is_kid=validated_data.get('is_kid', False),
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class KidSummarySerializer(serializers.ModelSerializer):
    pending_tasks = serializers.SerializerMethodField()
    completed_tasks = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'points', 'avatar_color', 'pending_tasks', 'completed_tasks']

    def get_pending_tasks(self, obj):
        return obj.tasks.filter(completed=False).count()

    def get_completed_tasks(self, obj):
        return obj.tasks.filter(completed=True).count()
