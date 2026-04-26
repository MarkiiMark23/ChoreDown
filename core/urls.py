from django.urls import path
from . import views

urlpatterns = [
    # --- Web views ---
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/parent/', views.parent_dashboard_view, name='parent_dashboard'),
    path('dashboard/kid/', views.kid_dashboard_view, name='kid_dashboard'),

    path('kids/add/', views.add_kid_view, name='add_kid'),

    path('tasks/', views.task_list_view, name='task_list'),
    path('tasks/create/', views.task_create_view, name='task_create'),
    path('tasks/<int:pk>/complete/', views.task_complete_view, name='task_complete'),

    path('behaviors/', views.behavior_list_view, name='behavior_list'),
    path('behaviors/log/', views.behavior_log_view, name='behavior_log'),

    path('rewards/', views.reward_list_view, name='reward_list'),
    path('rewards/create/', views.reward_create_view, name='reward_create'),
    path('rewards/<int:pk>/redeem/', views.reward_redeem_view, name='reward_redeem'),

    path('redemptions/', views.redemption_list_view, name='redemption_list'),
    path('redemptions/<int:pk>/<str:action>/', views.redemption_resolve_view, name='redemption_resolve'),

    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),

    # --- API views ---
    path('api/register/', views.UserRegistrationView.as_view(), name='api_register'),
    path('api/login/', views.CustomAuthToken.as_view(), name='api_login'),
    path('api/tasks/', views.TaskListAPIView.as_view(), name='api_task_list'),
    path('api/tasks/create/', views.TaskCreateAPIView.as_view(), name='api_task_create'),
    path('api/tasks/<int:pk>/complete/', views.TaskCompleteAPIView.as_view(), name='api_task_complete'),
    path('api/behaviors/log/', views.BehaviorLogAPIView.as_view(), name='api_behavior_log'),
    path('api/rewards/', views.RewardListAPIView.as_view(), name='api_reward_list'),
    path('api/leaderboard/', views.LeaderboardAPIView.as_view(), name='api_leaderboard'),
    path('api/points/history/', views.PointHistoryAPIView.as_view(), name='api_point_history'),
]
