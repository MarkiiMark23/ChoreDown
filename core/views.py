from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils import timezone
from django.db import transaction as db_transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status, generics, permissions
from rest_framework.permissions import IsAuthenticated

from .models import CustomUser, Task, Behavior, Reward, RewardRedemption, PointTransaction
from .serializers import (
    TaskSerializer, TaskCompleteSerializer, BehaviorSerializer,
    RewardSerializer, RewardRedemptionSerializer, PointTransactionSerializer,
    UserRegistrationSerializer, KidSummarySerializer,
)
from .permissions import IsParent, IsKid
from .forms import ParentRegistrationForm, AddKidForm, TaskCreateForm, BehaviorLogForm, RewardCreateForm, TaskCompleteForm, ProfileEditForm


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
        user = form.save(commit=False)
        join_code = form.cleaned_data.get('join_family_code', '').strip().upper()
        if join_code:
            try:
                head = CustomUser.objects.get(
                    family_code=join_code, is_parent=True, parent_account=None
                )
                user.parent_account = head
            except CustomUser.DoesNotExist:
                form.add_error('join_family_code', 'Invalid family code — check with your partner.')
                return render(request, 'core/register.html', {'form': form})
        user.save()
        login(request, user)
        messages.success(request, f"Welcome, {user.first_name or user.username}! Add your kids to get started.")
        return redirect('dashboard')
    return render(request, 'core/register.html', {'form': form})


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
    head = request.user.get_family_head()
    kids = request.user.get_family_kids()
    pending_redemptions = RewardRedemption.objects.filter(
        reward__parent=head, status='pending'
    ).select_related('kid', 'reward').order_by('-requested_at')
    recent_tasks = Task.objects.filter(
        parent=head
    ).select_related('assigned_to').order_by('-id')[:10]
    kids_sorted = kids.order_by('-points')
    context = {
        'kids': kids,
        'kids_sorted': kids_sorted,
        'pending_redemptions': pending_redemptions,
        'recent_tasks': recent_tasks,
        'total_tasks_today': Task.objects.filter(
            parent=head,
            completed=True,
            completed_at__date=timezone.now().date()
        ).count(),
    }
    return render(request, 'core/parent_dashboard.html', context)


@login_required
def kid_dashboard_view(request):
    if not request.user.is_kid:
        return redirect('parent_dashboard')
    kid = request.user
    head = kid.get_family_head()
    pending_tasks = Task.objects.filter(assigned_to=kid, completed=False).order_by('due_date')
    completed_tasks = Task.objects.filter(assigned_to=kid, completed=True).order_by('-completed_at')[:5]
    recent_transactions = kid.point_transactions.all()[:8]
    available_rewards = []
    if kid.parent_account_id:
        available_rewards = Reward.objects.filter(parent=head, is_active=True).order_by('points_cost')
    pending_redemptions = RewardRedemption.objects.filter(kid=kid, status='pending')
    siblings = kid.get_family_kids().order_by('-points') if kid.parent_account_id else []
    context = {
        'kid': kid,
        'pending_tasks': pending_tasks,
        'completed_tasks': completed_tasks,
        'recent_transactions': recent_transactions,
        'available_rewards': available_rewards,
        'pending_redemptions': pending_redemptions,
        'siblings': siblings,
        'affordable_rewards': [r for r in available_rewards if r.points_cost <= kid.points],
    }
    return render(request, 'core/kid_dashboard.html', context)


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


@login_required
def task_list_view(request):
    if request.user.is_parent:
        tasks = Task.objects.filter(
            parent=request.user.get_family_head()
        ).select_related('assigned_to').order_by('-id')
    else:
        tasks = Task.objects.filter(assigned_to=request.user).order_by('due_date')
    return render(request, 'core/tasks.html', {'tasks': tasks})


@login_required
def task_create_view(request):
    if not request.user.is_parent:
        return redirect('dashboard')
    form = TaskCreateForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        task = form.save(commit=False)
        task.parent = request.user.get_family_head()
        task.save()
        messages.success(request, f"Task '{task.title}' assigned!")
        return redirect('task_list')
    return render(request, 'core/task_create.html', {'form': form})


@login_required
def task_complete_view(request, pk):
    if not request.user.is_kid:
        return redirect('dashboard')
    task = get_object_or_404(Task, pk=pk, assigned_to=request.user, completed=False)
    form = TaskCompleteForm(request.POST or None, instance=task)
    if request.method == 'POST' and form.is_valid():
        with db_transaction.atomic():
            t = form.save(commit=False)
            t.completed = True
            t.completed_at = timezone.now()
            t.finished_late = timezone.now() > task.due_date
            t.save()
            points_earned = task.points_value
            penalty = 0
            if t.did_not_finish:
                penalty = task.points_value // 2
                points_earned = 0
            elif t.not_quite:
                penalty = task.points_value // 4
                points_earned = task.points_value - penalty
            elif t.finished_late:
                penalty = task.points_value // 4
                points_earned = task.points_value - penalty
            if points_earned > 0:
                _award_points(request.user, points_earned, 'task', f"Completed: {task.title}")
            if penalty > 0:
                _award_points(request.user, -penalty, 'penalty', f"Penalty: {task.title}")
        messages.success(request, f"Great job! You earned {points_earned} points!")
        return redirect('kid_dashboard')
    return render(request, 'core/task_complete.html', {'task': task, 'form': form})


@login_required
def behavior_list_view(request):
    if not request.user.is_parent:
        return redirect('dashboard')
    family_kid_ids = request.user.get_family_kids().values_list('id', flat=True)
    behaviors = Behavior.objects.filter(
        associated_with_id__in=family_kid_ids
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


@login_required
def reward_list_view(request):
    if request.user.is_parent:
        head = request.user.get_family_head()
        rewards = Reward.objects.filter(parent=head).order_by('points_cost')
        return render(request, 'core/rewards_manage.html', {'rewards': rewards})
    if not request.user.parent_account_id:
        return render(request, 'core/rewards.html', {'rewards': [], 'no_parent': True})
    head = request.user.get_family_head()
    rewards = Reward.objects.filter(parent=head, is_active=True).order_by('points_cost')
    pending_ids = set(
        RewardRedemption.objects.filter(kid=request.user, status='pending').values_list('reward_id', flat=True)
    )
    return render(request, 'core/rewards.html', {
        'rewards': rewards,
        'pending_ids': pending_ids,
        'kid_points': request.user.points,
    })


@login_required
def reward_create_view(request):
    if not request.user.is_parent:
        return redirect('dashboard')
    form = RewardCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        reward = form.save(commit=False)
        reward.parent = request.user.get_family_head()
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
        RewardRedemption.objects.create(kid=request.user, reward=reward)
        messages.success(request, f"Redemption request sent to your parent!")
        return redirect('kid_dashboard')
    return render(request, 'core/reward_redeem_confirm.html', {'reward': reward})


@login_required
def redemption_list_view(request):
    if not request.user.is_parent:
        return redirect('dashboard')
    head = request.user.get_family_head()
    pending = RewardRedemption.objects.filter(
        reward__parent=head, status='pending'
    ).select_related('kid', 'reward').order_by('-requested_at')
    resolved = RewardRedemption.objects.filter(
        reward__parent=head
    ).exclude(status='pending').select_related('kid', 'reward').order_by('-resolved_at')[:20]
    return render(request, 'core/redemptions.html', {'pending': pending, 'resolved': resolved})


@login_required
def redemption_resolve_view(request, pk, action):
    if not request.user.is_parent:
        return redirect('dashboard')
    head = request.user.get_family_head()
    redemption = get_object_or_404(RewardRedemption, pk=pk, reward__parent=head, status='pending')
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
            messages.success(request, f"Approved! {redemption.kid.first_name or redemption.kid.username} spent {redemption.reward.points_cost} pts.")
        else:
            messages.info(request, "Redemption denied.")
    return redirect('redemption_list')


@login_required
def leaderboard_view(request):
    kids = request.user.get_family_kids().order_by('-points')
    return render(request, 'core/leaderboard.html', {'kids': kids, 'current_kid': request.user})


@login_required
def profile_view(request):
    user = request.user
    transactions = user.point_transactions.all()[:20]
    stats = {}
    if user.is_kid:
        stats['tasks_done'] = Task.objects.filter(assigned_to=user, completed=True).count()
        stats['tasks_pending'] = Task.objects.filter(assigned_to=user, completed=False).count()
        stats['rewards_redeemed'] = RewardRedemption.objects.filter(kid=user, status='approved').count()
        stats['total_earned'] = sum(
            t.amount for t in user.point_transactions.filter(amount__gt=0)
        )
    if user.is_parent:
        head = user.get_family_head()
        kids = user.get_family_kids()
        stats['kids_count'] = kids.count()
        stats['tasks_total'] = Task.objects.filter(parent=head).count()
        stats['tasks_done'] = Task.objects.filter(parent=head, completed=True).count()
        stats['rewards_created'] = Reward.objects.filter(parent=head).count()
    return render(request, 'core/profile.html', {'transactions': transactions, 'stats': stats})


@login_required
def profile_edit_view(request):
    form = ProfileEditForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Profile updated!")
        return redirect('profile')
    return render(request, 'core/profile_edit.html', {'form': form})


class TaskCompleteAPIView(generics.UpdateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskCompleteSerializer
    permission_classes = [IsAuthenticated, IsKid]

    def get_queryset(self):
        return Task.objects.filter(assigned_to=self.request.user)

    def perform_update(self, serializer):
        task = self.get_object()
        with db_transaction.atomic():
            instance = serializer.save(completed=True, completed_at=timezone.now())
            points_earned = task.points_value
            if instance.did_not_finish:
                points_earned = 0
                _award_points(self.request.user, -(task.points_value // 2), 'penalty', f"Did not finish: {task.title}")
            elif instance.not_quite:
                penalty = task.points_value // 4
                points_earned = task.points_value - penalty
                _award_points(self.request.user, points_earned, 'task', f"Completed: {task.title}")
            else:
                _award_points(self.request.user, points_earned, 'task', f"Completed: {task.title}")


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
        kids = request.user.get_family_kids().order_by('-points')
        serializer = KidSummarySerializer(kids, many=True)
        return Response(serializer.data)


class RewardListAPIView(generics.ListAPIView):
    serializer_class = RewardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_kid and self.request.user.parent_account_id:
            return Reward.objects.filter(parent=self.request.user.get_family_head(), is_active=True)
        if self.request.user.is_parent:
            return Reward.objects.filter(parent=self.request.user.get_family_head())
        return Reward.objects.none()


class PointHistoryAPIView(generics.ListAPIView):
    serializer_class = PointTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.point_transactions.all()


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
