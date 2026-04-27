# Generated for ChoreDown task review and notification workflow.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_behavior_points_value_customuser_avatar_color_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="age_range",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="customuser",
            name="best_task_time",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="customuser",
            name="default_approval_note",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="customuser",
            name="favorite_rewards",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="customuser",
            name="feedback_preferences",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="customuser",
            name="focus_supports",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="customuser",
            name="goals",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="customuser",
            name="household_timezone",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="customuser",
            name="motivation_style",
            field=models.CharField(
                blank=True,
                choices=[
                    ("points", "Points and progress"),
                    ("praise", "Praise and encouragement"),
                    ("rewards", "Rewards"),
                    ("choice", "Choice and independence"),
                    ("quiet", "Quiet completion"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="notification_preference",
            field=models.CharField(
                choices=[
                    ("in_app", "In-app only"),
                    ("email", "Email only"),
                    ("both", "In-app and email"),
                    ("none", "No notifications"),
                ],
                default="in_app",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="overwhelm_triggers",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="customuser",
            name="preferred_name",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="customuser",
            name="reminder_preference",
            field=models.CharField(
                blank=True,
                choices=[
                    ("gentle", "Gentle reminders"),
                    ("visual", "Visual checklist"),
                    ("countdown", "Countdown"),
                    ("direct", "Direct reminder"),
                    ("none", "No reminder preference"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="sensory_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="task",
            name="effort_note",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="task",
            name="parent_feedback",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="task",
            name="points_earned",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_tasks",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="status",
            field=models.CharField(
                choices=[
                    ("assigned", "Assigned"),
                    ("submitted", "Submitted for Review"),
                    ("approved", "Approved"),
                    ("rejected", "Needs Another Try"),
                ],
                default="assigned",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="submitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "notification_type",
                    models.CharField(
                        choices=[
                            ("task_submitted", "Task Submitted"),
                            ("task_approved", "Task Approved"),
                            ("task_rejected", "Task Needs Another Try"),
                            ("reward_requested", "Reward Requested"),
                            ("reward_approved", "Reward Approved"),
                            ("reward_denied", "Reward Denied"),
                            ("points_changed", "Points Changed"),
                            ("system", "System"),
                        ],
                        max_length=30,
                    ),
                ),
                ("title", models.CharField(max_length=120)),
                ("message", models.TextField()),
                ("deliver_in_app", models.BooleanField(default=True)),
                ("is_read", models.BooleanField(default=False)),
                (
                    "email_status",
                    models.CharField(
                        choices=[
                            ("not_requested", "Not requested"),
                            ("queued", "Queued"),
                            ("sent", "Sent"),
                            ("skipped", "Skipped"),
                            ("failed", "Failed"),
                        ],
                        default="not_requested",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sent_notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "recipient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reward_redemption",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to="core.rewardredemption",
                    ),
                ),
                (
                    "task",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to="core.task",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
