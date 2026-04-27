from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils import timezone
from django.db import transaction as db_transaction
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status, generics, permissions
from rest_framework.permissions import IsAuthenticated

from .models import CustomUser, Task, Behavior, Reward, RewardRedemption, PointTransaction, Notification
from .serializers import (
    TaskSerializer, TaskCompleteSerializer, BehaviorSerializer,
    RewardSerializer, RewardRedemptionSerializer, PointTransactionSerializer, NotificationSerializer,
    UserRegistrationSerializer, KidSummarySerializer,
)
from .permissions import IsParent, IsKid
from .forms import (
    ParentRegistrationForm, AddKidForm, TaskCreateForm, BehaviorLogForm,
    RewardCreateForm, TaskCompleteForm, TaskReviewForm, ProfileForm,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _award_points(user, amount, transaction_type, description):
    """Add or subtract points and record the transaction."""
    user.points = max(0, user.points + amount)
    user.save(update_fields=['points'])
    PointTransaction.objects.create(
        user=user,
        amount=amount,
        transaction_type=transaction_type,
        description=description,
    )


def _suggested_task_points(task):
    points_earned = task.points_value
    if task.did_not_finish:
        points_earned = 0
    elif task.not_quite or task.finished_late:
        points_earned = task.points_value - (task.points_value // 4)
    return points_earned


def _create_notification(recipient, notification_type, title, message, actor=None, task=None, reward_redemption=None):
    preference = recipient.notification_preference or 'in_app'
    if preference == 'none':
        return None
    deliver_in_app = preference in ('in_app', 'both')
    email_status = 'queued' if preference in ('email', 'both') and recipient.email else 'skipped'
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        title=title,
        message=message,
        deliver_in_app=deliver_in_app,
        task=task,
        reward_redemption=reward_redemption,
        email_status=email_status,
    )


def _kid_display_name(user):
    return user.preferred_name or user.first_name or user.username


# ---------------------------------------------------------------------------
# Auth views
# ---------------------------------------------------------------------------

def home_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('dashboard')
    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = ParentRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome, {user.first_name or user.username}! Add your kids to get started.")
        return redirect('dashboard')
    return render(request, 'core/register.html', {'form': form})


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard_view(request):
    if request.user.is_parent:
        return redirect('parent_dashboard')
    if request.user.is_kid:
        return redirect('kid_dashboard')
    return redirect('login')


@login_required
def parent_dashboard_view(request):
    if not request.user.is_parent:
        return redirect('kid_dashboard')
    kids = request.user.children.filter(is_kid=True)
    pending_reviews = Task.objects.filter(
        parent=request.user, status='submitted'
    ).select_related('assigned_to').order_by('submitted_at')
    pending_redemptions = RewardRedemption.objects.filter(
        reward__parent=request.user, status='pending'
    ).select_related('kid', 'reward').order_by('-requested_at')
    recent_tasks = Task.objects.filter(
        parent=request.user
    ).select_related('assigned_to').order_by('-id')[:10]
    recent_behaviors = Behavior.objects.filter(
        logged_by=request.user
    ).select_related('associated_with').order_by('-date_logged')[:5]
    kids_sorted = kids.order_by('-points')
    reviewed_tasks = Task.objects.filter(parent=request.user, status='approved')
    possible_points_awarded = sum(t.points_value for t in reviewed_tasks)
    actual_points_awarded = sum(t.points_earned or 0 for t in reviewed_tasks)
    total_tasks = Task.objects.filter(parent=request.user).count()
    completed_count = Task.objects.filter(parent=request.user, status='approved').count()
    context = {
        'kids': kids,
        'kids_sorted': kids_sorted,
        'pending_reviews': pending_reviews,
        'pending_redemptions': pending_redemptions,
        'recent_tasks': recent_tasks,
        'recent_behaviors': recent_behaviors,
        'possible_points_awarded': possible_points_awarded,
        'actual_points_awarded': actual_points_awarded,
        'completion_rate': round((completed_count / total_tasks) * 100) if total_tasks else 0,
        'late_or_partial_count': Task.objects.filter(
            parent=request.user,
            status='approved',
        ).filter(Q(finished_late=True) | Q(not_quite=True) | Q(did_not_finish=True)).count(),
        'total_tasks_today': Task.objects.filter(
            parent=request.user,
            status='approved',
            completed_at__date=timezone.now().date()
        ).count(),
    }
    return render(request, 'core/parent_dashboard.html', context)


@login_required
def kid_dashboard_view(request):
    if not request.user.is_kid:
        return redirect('parent_dashboard')
    kid = request.user
    pending_tasks = Task.objects.filter(assigned_to=kid, status__in=['assigned', 'rejected']).order_by('due_date')
    submitted_tasks = Task.objects.filter(assigned_to=kid, status='submitted').order_by('submitted_at')
    completed_tasks = Task.objects.filter(assigned_to=kid, status='approved').order_by('-completed_at')[:5]
    recent_transactions = kid.point_transactions.all()[:8]
    recent_notifications = kid.notifications.filter(deliver_in_app=True)[:5]
    available_rewards = []
    if kid.parent_account:
        available_rewards = Reward.objects.filter(
            parent=kid.parent_account, is_active=True
        ).order_by('points_cost')
    pending_redemptions = RewardRedemption.objects.filter(kid=kid, status='pending')
    siblings = []
    if kid.parent_account:
        siblings = kid.parent_account.children.filter(is_kid=True).order_by('-points')
    affordable_rewards = [r for r in available_rewards if r.points_cost <= kid.points]
    unaffordable_rewards = [r for r in available_rewards if r.points_cost > kid.points]
    next_unaffordable_reward = unaffordable_rewards[0] if unaffordable_rewards and not affordable_rewards else None
    context = {
        'kid': kid,
        'pending_tasks': pending_tasks,
        'submitted_tasks': submitted_tasks,
        'completed_tasks': completed_tasks,
        'recent_transactions': recent_transactions,
        'recent_notifications': recent_notifications,
        'available_rewards': available_rewards,
        'pending_redemptions': pending_redemptions,
        'siblings': siblings,
        'affordable_rewards': affordable_rewards,
        'next_unaffordable_reward': next_unaffordable_reward,
        'next_task': pending_tasks.first(),
    }
    return render(request, 'core/kid_dashboard.html', context)


# ---------------------------------------------------------------------------
# Kid management (parent)
# ---------------------------------------------------------------------------

@login_required
def add_kid_view(request):
    if not request.user.is_parent:
        return redirect('dashboard')
    form = AddKidForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        kid = form.save(parent=request.user)
        messages.success(request, f"Added {kid.first_name or kid.username} to your family!")
        return redirect('parent_dashboard')
    return render(request, 'core/add_kid.html', {'form': form})


# ---------------------------------------------------------------------------
# Task views
# ---------------------------------------------------------------------------

@login_required
def task_list_view(request):
    if request.user.is_parent:
        tasks = Task.objects.filter(parent=request.user).select_related('assigned_to').order_by('-id')
        kid_id = request.GET.get('kid')
        if kid_id:
            tasks = tasks.filter(assigned_to_id=kid_id)
    else:
        tasks = Task.objects.filter(assigned_to=request.user).order_by('due_date')
    return render(request, 'core/tasks.html', {'tasks': tasks, 'status_filter': request.GET.get('status', 'all')})


@login_required
def task_create_view(request):
    if not request.user.is_parent:
        return redirect('dashboard')
    form = TaskCreateForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        task = form.save(commit=False)
        task.parent = request.user
        task.save()
        messages.success(request, f"Task '{task.title}' assigned!")
        return redirect('task_list')
    return render(request, 'core/task_create.html', {'form': form})


@login_required
def task_complete_view(request, pk):
    if not request.user.is_kid:
        return redirect('dashboard')
    task = get_object_or_404(Task, pk=pk, assigned_to=request.user, status__in=['assigned', 'rejected'])
    form = TaskCompleteForm(request.POST or None, instance=task)
    if request.method == 'POST' and form.is_valid():
        with db_transaction.atomic():
            t = form.save(commit=False)
            t.completed = False
            t.completed_at = None
            t.status = 'submitted'
            t.submitted_at = timezone.now()
            t.reviewed_at = None
            t.reviewed_by = None
            t.parent_feedback = ''
            t.points_earned = None
            t.finished_late = timezone.now() > task.due_date
            t.save()
            _create_notification(
                recipient=t.parent,
                actor=request.user,
                notification_type='task_submitted',
                title='Task ready to review',
                message=f"{_kid_display_name(request.user)} submitted '{task.title}' for review.",
                task=t,
            )
        messages.success(request, f"Nice follow-through. Sent to parent for review. Possible reward: {task.points_value} pts.")
        return redirect('kid_dashboard')
    return render(request, 'core/task_complete.html', {'task': task, 'form': form})


@login_required
def task_review_view(request, pk):
    if not request.user.is_parent:
        return redirect('dashboard')
    task = get_object_or_404(
        Task.objects.select_related('assigned_to'),
        pk=pk,
        parent=request.user,
        status='submitted',
    )
    suggested_points = _suggested_task_points(task)
    if request.method == 'POST':
        action = request.POST.get('action')
        form = TaskReviewForm(request.POST, instance=task)
        if action == 'reject':
            feedback = request.POST.get('parent_feedback', '').strip()
            with db_transaction.atomic():
                task.status = 'rejected'
                task.completed = False
                task.points_earned = 0
                task.reviewed_at = timezone.now()
                task.reviewed_by = request.user
                task.parent_feedback = feedback
                task.save(update_fields=[
                    'status', 'completed', 'points_earned', 'reviewed_at',
                    'reviewed_by', 'parent_feedback',
                ])
                PointTransaction.objects.create(
                    user=task.assigned_to,
                    amount=0,
                    transaction_type='task',
                    description=f"Needs another try: {task.title}",
                )
                _create_notification(
                    recipient=task.assigned_to,
                    actor=request.user,
                    notification_type='task_rejected',
                    title='Task needs another try',
                    message=feedback or f"'{task.title}' needs one more try before points are awarded.",
                    task=task,
                )
            messages.info(request, f"Sent {_kid_display_name(task.assigned_to)} a reset note for '{task.title}'.")
            return redirect('parent_dashboard')
        if form.is_valid():
            reviewed_task = form.save(commit=False)
            with db_transaction.atomic():
                reviewed_task.status = 'approved'
                reviewed_task.completed = True
                reviewed_task.completed_at = timezone.now()
                reviewed_task.reviewed_at = timezone.now()
                reviewed_task.reviewed_by = request.user
                reviewed_task.save()
                tx_type = 'task' if reviewed_task.points_earned >= 0 else 'penalty'
                _award_points(
                    reviewed_task.assigned_to,
                    reviewed_task.points_earned,
                    tx_type,
                    f"Approved: {reviewed_task.title} ({reviewed_task.points_earned}/{reviewed_task.points_value} pts)",
                )
                _create_notification(
                    recipient=reviewed_task.assigned_to,
                    actor=request.user,
                    notification_type='task_approved',
                    title='Task approved',
                    message=(
                        f"'{reviewed_task.title}' was approved. "
                        f"You earned {reviewed_task.points_earned} of {reviewed_task.points_value} possible points."
                    ),
                    task=reviewed_task,
                )
            messages.success(
                request,
                f"Approved '{reviewed_task.title}' for {reviewed_task.points_earned} actual points.",
            )
            return redirect('parent_dashboard')
    else:
        form = TaskReviewForm(instance=task, initial={'points_earned': suggested_points})
    return render(request, 'core/task_review.html', {
        'task': task,
        'form': form,
        'suggested_points': suggested_points,
    })


# ---------------------------------------------------------------------------
# Behavior views
# ---------------------------------------------------------------------------

@login_required
def behavior_list_view(request):
    if not request.user.is_parent:
        return redirect('dashboard')
    behaviors = Behavior.objects.filter(
        logged_by=request.user
    ).select_related('associated_with').order_by('-date_logged')
    return render(request, 'core/behaviors.html', {'behaviors': behaviors})


@login_required
def behavior_log_view(request):
    if not request.user.is_parent:
        return redirect('dashboard')
    form = BehaviorLogForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with db_transaction.atomic():
            behavior = form.save(commit=False)
            behavior.logged_by = request.user
            behavior.save()
            kid = behavior.associated_with
            if behavior.behavior_type == 'positive':
                _award_points(kid, behavior.points_value, 'behavior_positive', behavior.description)
                messages.success(request, f"Added {behavior.points_value} pts to {kid.first_name or kid.username}.")
            else:
                _award_points(kid, -behavior.points_value, 'behavior_negative', behavior.description)
                messages.warning(request, f"Removed {behavior.points_value} pts from {kid.first_name or kid.username}.")
        return redirect('behavior_list')
    return render(request, 'core/behavior_log.html', {'form': form})


# ---------------------------------------------------------------------------
# Reward views
# ---------------------------------------------------------------------------

@login_required
def reward_list_view(request):
    if request.user.is_parent:
        rewards = Reward.objects.filter(parent=request.user).order_by('points_cost')
        return render(request, 'core/rewards_manage.html', {'rewards': rewards})
    # Kid view
    if not request.user.parent_account:
        return render(request, 'core/rewards.html', {'rewards': [], 'no_parent': True})
    rewards = Reward.objects.filter(parent=request.user.parent_account, is_active=True).order_by('points_cost')
    pending_ids = set(
        RewardRedemption.objects.filter(kid=request.user, status='pending').values_list('reward_id', flat=True)
    )
    kid_points = request.user.points
    unaffordable = [r for r in rewards if r.points_cost > kid_points]
    closest_reward = unaffordable[0] if unaffordable else None
    closest_gap = (closest_reward.points_cost - kid_points) if closest_reward else 0
    return render(request, 'core/rewards.html', {
        'rewards': rewards,
        'pending_ids': pending_ids,
        'kid_points': kid_points,
        'closest_reward': closest_reward,
        'closest_gap': closest_gap,
    })


@login_required
def reward_create_view(request):
    if not request.user.is_parent:
        return redirect('dashboard')
    form = RewardCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        reward = form.save(commit=False)
        reward.parent = request.user
        reward.save()
        messages.success(request, f"Reward '{reward.title}' created!")
        return redirect('reward_list')
    return render(request, 'core/reward_create.html', {'form': form})


@login_required
def reward_redeem_view(request, pk):
    if not request.user.is_kid:
        return redirect('dashboard')
    reward = get_object_or_404(Reward, pk=pk, is_active=True)
    if request.user.points < reward.points_cost:
        messages.error(request, "You don't have enough points for this reward yet!")
        return redirect('reward_list')
    already_pending = RewardRedemption.objects.filter(kid=request.user, reward=reward, status='pending').exists()
    if already_pending:
        messages.info(request, "You already have a pending request for this reward.")
        return redirect('reward_list')
    if request.method == 'POST':
        redemption = RewardRedemption.objects.create(kid=request.user, reward=reward)
        _create_notification(
            recipient=reward.parent,
            actor=request.user,
            notification_type='reward_requested',
            title='New reward request',
            message=f"{_kid_display_name(request.user)} requested '{reward.title}' for {reward.points_cost} pts.",
            reward_redemption=redemption,
        )
        messages.success(request, f"Redemption request sent to your parent!")
        return redirect('kid_dashboard')
    return render(request, 'core/reward_redeem_confirm.html', {'reward': reward})


# ---------------------------------------------------------------------------
# Redemption management (parent)
# ---------------------------------------------------------------------------

@login_required
def redemption_list_view(request):
    if not request.user.is_parent:
        return redirect('dashboard')
    pending = RewardRedemption.objects.filter(
        reward__parent=request.user, status='pending'
    ).select_related('kid', 'reward').order_by('-requested_at')
    resolved = RewardRedemption.objects.filter(
        reward__parent=request.user
    ).exclude(status='pending').select_related('kid', 'reward').order_by('-resolved_at')[:20]
    return render(request, 'core/redemptions.html', {'pending': pending, 'resolved': resolved})


@login_required
def redemption_resolve_view(request, pk, action):
    if not request.user.is_parent:
        return redirect('dashboard')
    redemption = get_object_or_404(RewardRedemption, pk=pk, reward__parent=request.user, status='pending')
    if action not in ('approve', 'deny'):
        return redirect('redemption_list')
    with db_transaction.atomic():
        redemption.status = 'approved' if action == 'approve' else 'denied'
        redemption.resolved_at = timezone.now()
        redemption.resolved_by = request.user
        redemption.save()
        if action == 'approve':
            _award_points(
                redemption.kid,
                -redemption.reward.points_cost,
                'redemption',
                f"Redeemed: {redemption.reward.title}"
            )
            _create_notification(
                recipient=redemption.kid,
                actor=request.user,
                notification_type='reward_approved',
                title='Reward approved',
                message=f"Your request for '{redemption.reward.title}' was approved.",
                reward_redemption=redemption,
            )
            messages.success(request, f"Approved! {redemption.kid.first_name or redemption.kid.username} spent {redemption.reward.points_cost} pts.")
        else:
            _create_notification(
                recipient=redemption.kid,
                actor=request.user,
                notification_type='reward_denied',
                title='Reward request denied',
                message=f"Your request for '{redemption.reward.title}' was denied this time.",
                reward_redemption=redemption,
            )
            messages.info(request, "Redemption denied.")
    return redirect('redemption_list')


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

@login_required
def leaderboard_view(request):
    if request.user.is_parent:
        kids = request.user.children.filter(is_kid=True).order_by('-points')
    else:
        kids = []
        if request.user.parent_account:
            kids = request.user.parent_account.children.filter(is_kid=True).order_by('-points')
    return render(request, 'core/leaderboard.html', {'kids': kids, 'current_kid': request.user})


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@login_required
def profile_view(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated.')
        return redirect('profile')
    transactions = request.user.point_transactions.all()[:20]
    return render(request, 'core/profile.html', {'transactions': transactions, 'form': form})


@login_required
def notification_list_view(request):
    notifications = request.user.notifications.filter(deliver_in_app=True)
    return render(request, 'core/notifications.html', {'notifications': notifications})


@login_required
def notification_read_view(request, pk):
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user,
        deliver_in_app=True,
    )
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at'])
    if notification.task_id:
        if request.user.is_parent:
            return redirect('task_list')
        return redirect('kid_dashboard')
    if notification.reward_redemption_id:
        if request.user.is_parent:
            return redirect('redemption_list')
        return redirect('reward_list')
    return redirect('notification_list')


@login_required
def point_history_view(request):
    if request.user.is_parent:
        kid_ids = list(request.user.children.filter(is_kid=True).values_list('id', flat=True))
        transactions = PointTransaction.objects.filter(user_id__in=kid_ids).select_related('user')
    else:
        transactions = request.user.point_transactions.all()
    return render(request, 'core/point_history.html', {'transactions': transactions[:100]})


# ---------------------------------------------------------------------------
# API views
# ---------------------------------------------------------------------------

class TaskCompleteAPIView(generics.UpdateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskCompleteSerializer
    permission_classes = [IsAuthenticated, IsKid]

    def get_queryset(self):
        return Task.objects.filter(assigned_to=self.request.user, status__in=['assigned', 'rejected'])

    def perform_update(self, serializer):
        task = self.get_object()
        with db_transaction.atomic():
            instance = serializer.save(
                completed=False,
                completed_at=None,
                status='submitted',
                submitted_at=timezone.now(),
                reviewed_at=None,
                reviewed_by=None,
                points_earned=None,
                finished_late=timezone.now() > task.due_date,
            )
            _create_notification(
                recipient=instance.parent,
                actor=self.request.user,
                notification_type='task_submitted',
                title='Task ready to review',
                message=f"{_kid_display_name(self.request.user)} submitted '{task.title}' for review.",
                task=instance,
            )


class TaskCreateAPIView(generics.CreateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsParent]

    def perform_create(self, serializer):
        serializer.save(parent=self.request.user)


class TaskListAPIView(generics.ListAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsKid]

    def get_queryset(self):
        return Task.objects.filter(assigned_to=self.request.user)


class BehaviorLogAPIView(generics.CreateAPIView):
    queryset = Behavior.objects.all()
    serializer_class = BehaviorSerializer
    permission_classes = [IsAuthenticated, IsParent]

    def perform_create(self, serializer):
        with db_transaction.atomic():
            behavior = serializer.save(logged_by=self.request.user)
            kid = behavior.associated_with
            if behavior.behavior_type == 'positive':
                _award_points(kid, behavior.points_value, 'behavior_positive', behavior.description)
            else:
                _award_points(kid, -behavior.points_value, 'behavior_negative', behavior.description)


class LeaderboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_parent:
            kids = request.user.children.filter(is_kid=True).order_by('-points')
        elif request.user.parent_account:
            kids = request.user.parent_account.children.filter(is_kid=True).order_by('-points')
        else:
            kids = CustomUser.objects.none()
        serializer = KidSummarySerializer(kids, many=True)
        return Response(serializer.data)


class RewardListAPIView(generics.ListAPIView):
    serializer_class = RewardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_kid and self.request.user.parent_account:
            return Reward.objects.filter(parent=self.request.user.parent_account, is_active=True)
        if self.request.user.is_parent:
            return Reward.objects.filter(parent=self.request.user)
        return Reward.objects.none()


class PointHistoryAPIView(generics.ListAPIView):
    serializer_class = PointTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.point_transactions.all()


class NotificationListAPIView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.notifications.filter(deliver_in_app=True)


class UserRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User registered successfully!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomAuthToken(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if not user:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user_id': user.id, 'username': user.username})
