from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import CustomUser, Notification, PointTransaction, Reward, RewardRedemption, Task


class TaskReviewWorkflowTests(TestCase):
    def setUp(self):
        self.parent = CustomUser.objects.create_user(
            username='parent',
            password='pass12345',
            is_parent=True,
            email='parent@example.com',
        )
        self.kid = CustomUser.objects.create_user(
            username='kid',
            password='pass12345',
            is_kid=True,
            parent_account=self.parent,
            notification_preference='in_app',
        )
        self.task = Task.objects.create(
            title='Clean room',
            due_date=timezone.now() + timedelta(days=1),
            points_value=10,
            parent=self.parent,
            assigned_to=self.kid,
        )

    def test_kid_submission_does_not_award_points_until_parent_review(self):
        self.client.force_login(self.kid)
        response = self.client.post(reverse('task_complete', args=[self.task.pk]), {
            'fun_rating': 4,
            'effort_note': 'I put everything away.',
        })

        self.assertRedirects(response, reverse('kid_dashboard'))
        self.kid.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(self.kid.points, 0)
        self.assertEqual(self.task.status, 'submitted')
        self.assertIsNone(self.task.points_earned)
        self.assertEqual(PointTransaction.objects.count(), 0)
        self.assertTrue(Notification.objects.filter(
            recipient=self.parent,
            notification_type='task_submitted',
            deliver_in_app=True,
        ).exists())

    def test_kid_can_submit_task_with_one_tap_empty_form(self):
        self.client.force_login(self.kid)
        response = self.client.post(reverse('task_complete', args=[self.task.pk]), {})

        self.assertRedirects(response, reverse('kid_dashboard'))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'submitted')
        self.assertIsNone(self.task.points_earned)

    def test_parent_approval_awards_actual_points_once(self):
        self.task.status = 'submitted'
        self.task.submitted_at = timezone.now()
        self.task.save()

        self.client.force_login(self.parent)
        response = self.client.post(reverse('task_review', args=[self.task.pk]), {
            'action': 'approve',
            'points_earned': 7,
            'parent_feedback': 'Good reset.',
        })

        self.assertRedirects(response, reverse('parent_dashboard'))
        self.kid.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(self.kid.points, 7)
        self.assertEqual(self.task.status, 'approved')
        self.assertEqual(self.task.points_earned, 7)
        self.assertEqual(PointTransaction.objects.get(user=self.kid).amount, 7)
        self.assertTrue(Notification.objects.filter(
            recipient=self.kid,
            notification_type='task_approved',
            message__contains='7 of 10',
        ).exists())

    def test_zero_point_approval_keeps_visible_history(self):
        self.task.status = 'submitted'
        self.task.submitted_at = timezone.now()
        self.task.save()

        self.client.force_login(self.parent)
        self.client.post(reverse('task_review', args=[self.task.pk]), {
            'action': 'approve',
            'points_earned': 0,
            'parent_feedback': 'Thanks for trying.',
        })

        self.kid.refresh_from_db()
        self.task.refresh_from_db()
        tx = PointTransaction.objects.get(user=self.kid)
        self.assertEqual(self.kid.points, 0)
        self.assertEqual(self.task.points_earned, 0)
        self.assertEqual(tx.amount, 0)
        self.assertIn('Approved', tx.description)

    def test_parent_rejection_notifies_kid_without_points(self):
        self.task.status = 'submitted'
        self.task.submitted_at = timezone.now()
        self.task.save()

        self.client.force_login(self.parent)
        response = self.client.post(reverse('task_review', args=[self.task.pk]), {
            'action': 'reject',
            'points_earned': 0,
            'parent_feedback': 'Please check under the bed.',
        })

        self.assertRedirects(response, reverse('parent_dashboard'))
        self.kid.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(self.kid.points, 0)
        self.assertEqual(self.task.status, 'rejected')
        self.assertTrue(Notification.objects.filter(
            recipient=self.kid,
            notification_type='task_rejected',
            message__contains='under the bed',
        ).exists())

    def test_parent_can_approve_all_waiting_tasks(self):
        second_task = Task.objects.create(
            title='Dishes',
            points_value=6,
            parent=self.parent,
            assigned_to=self.kid,
            status='submitted',
            submitted_at=timezone.now(),
        )
        self.task.status = 'submitted'
        self.task.submitted_at = timezone.now()
        self.task.save()

        self.client.force_login(self.parent)
        response = self.client.post(reverse('parent_dashboard'), {
            'action': 'approve_all_submitted',
        })

        self.assertRedirects(response, reverse('parent_dashboard'))
        self.kid.refresh_from_db()
        self.task.refresh_from_db()
        second_task.refresh_from_db()
        self.assertEqual(self.kid.points, 16)
        self.assertEqual(self.task.status, 'approved')
        self.assertEqual(second_task.status, 'approved')
        self.assertEqual(PointTransaction.objects.filter(user=self.kid).count(), 2)

    def test_parent_cannot_review_another_family_task(self):
        other_parent = CustomUser.objects.create_user(username='other', password='pass12345', is_parent=True)
        self.task.status = 'submitted'
        self.task.submitted_at = timezone.now()
        self.task.save()

        self.client.force_login(other_parent)
        response = self.client.get(reverse('task_review', args=[self.task.pk]))
        self.assertEqual(response.status_code, 404)


class RewardNotificationTests(TestCase):
    def setUp(self):
        self.parent = CustomUser.objects.create_user(
            username='parent',
            password='pass12345',
            is_parent=True,
        )
        self.kid = CustomUser.objects.create_user(
            username='kid',
            password='pass12345',
            is_kid=True,
            parent_account=self.parent,
            points=50,
            notification_preference='both',
            email='kid@example.com',
        )
        self.reward = Reward.objects.create(
            title='Movie pick',
            points_cost=25,
            parent=self.parent,
        )

    def test_reward_approval_creates_kid_notification_and_spends_points(self):
        redemption = RewardRedemption.objects.create(kid=self.kid, reward=self.reward)

        self.client.force_login(self.parent)
        response = self.client.get(reverse('redemption_resolve', args=[redemption.pk, 'approve']))

        self.assertRedirects(response, reverse('redemption_list'))
        self.kid.refresh_from_db()
        self.assertEqual(self.kid.points, 25)
        note = Notification.objects.get(recipient=self.kid, notification_type='reward_approved')
        self.assertTrue(note.deliver_in_app)
        self.assertEqual(note.email_status, 'queued')

    def test_reward_denial_respects_none_notification_preference(self):
        self.kid.notification_preference = 'none'
        self.kid.save()
        redemption = RewardRedemption.objects.create(kid=self.kid, reward=self.reward)

        self.client.force_login(self.parent)
        self.client.get(reverse('redemption_resolve', args=[redemption.pk, 'deny']))

        self.assertFalse(Notification.objects.filter(recipient=self.kid).exists())
