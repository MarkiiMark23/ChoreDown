from datetime import timedelta

from django.core import mail
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
        # Notification email is sent on transaction commit, so capture the callback.
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('redemption_resolve', args=[redemption.pk, 'approve']))

        self.assertRedirects(response, reverse('redemption_list'))
        self.kid.refresh_from_db()
        self.assertEqual(self.kid.points, 25)
        note = Notification.objects.get(recipient=self.kid, notification_type='reward_approved')
        self.assertTrue(note.deliver_in_app)
        # Kid prefers 'both' and has an email, so it should actually be sent.
        self.assertEqual(note.email_status, 'sent')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.kid.email, mail.outbox[0].to)

    def test_redemption_resolve_ignores_get_requests(self):
        # A GET (e.g. link prefetch or scanner) must not approve or deduct points.
        redemption = RewardRedemption.objects.create(kid=self.kid, reward=self.reward)

        self.client.force_login(self.parent)
        self.client.get(reverse('redemption_resolve', args=[redemption.pk, 'approve']))

        self.kid.refresh_from_db()
        redemption.refresh_from_db()
        self.assertEqual(self.kid.points, 50)            # unchanged
        self.assertEqual(redemption.status, 'pending')   # still pending

    def test_reward_denial_respects_none_notification_preference(self):
        self.kid.notification_preference = 'none'
        self.kid.save()
        redemption = RewardRedemption.objects.create(kid=self.kid, reward=self.reward)

        self.client.force_login(self.parent)
        self.client.post(reverse('redemption_resolve', args=[redemption.pk, 'deny']))

        self.assertFalse(Notification.objects.filter(recipient=self.kid).exists())

    def test_overspent_redemption_is_blocked_without_deducting(self):
        # Kid requested while affordable, then points dropped before parent approval.
        self.kid.points = 50
        self.kid.save()
        redemption = RewardRedemption.objects.create(kid=self.kid, reward=self.reward)  # cost 25
        self.kid.points = 10
        self.kid.save()

        self.client.force_login(self.parent)
        self.client.post(reverse('redemption_resolve', args=[redemption.pk, 'approve']))

        self.kid.refresh_from_db()
        redemption.refresh_from_db()
        self.assertEqual(self.kid.points, 10)            # nothing deducted
        self.assertEqual(redemption.status, 'pending')   # still pending


class PageRenderSmokeTests(TestCase):
    """Render every main page as a parent and a kid to catch template/url errors."""

    def setUp(self):
        self.parent = CustomUser.objects.create_user(
            username='smoke_parent', password='pass12345', is_parent=True,
        )
        self.kid = CustomUser.objects.create_user(
            username='smoke_kid', password='pass12345', is_kid=True,
            parent_account=self.parent, points=40,
        )
        self.reward = Reward.objects.create(title='Treat', points_cost=20, parent=self.parent)
        self.task = Task.objects.create(
            title='Tidy', points_value=10, parent=self.parent, assigned_to=self.kid,
        )

    def test_parent_pages_render(self):
        self.client.force_login(self.parent)
        # 'dashboard' is a role dispatcher that 302-redirects; tested separately below.
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)
        for name in [
            'parent_dashboard', 'add_kid', 'task_list', 'task_create',
            'behavior_list', 'behavior_log', 'reward_list', 'reward_create',
            'redemption_list', 'leaderboard', 'profile', 'notification_list',
            'point_history',
        ]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_kid_pages_render(self):
        self.client.force_login(self.kid)
        for name in [
            'dashboard', 'kid_dashboard', 'task_list', 'reward_list',
            'leaderboard', 'profile', 'notification_list', 'point_history',
        ]:
            with self.subTest(page=name):
                resp = self.client.get(reverse(name))
                # dashboard redirects kids to kid_dashboard; everything else is 200.
                self.assertIn(resp.status_code, (200, 302), name)
        # Kid-specific action pages.
        self.assertEqual(
            self.client.get(reverse('task_complete', args=[self.task.pk])).status_code, 200,
        )
        self.assertEqual(
            self.client.get(reverse('reward_redeem', args=[self.reward.pk])).status_code, 200,
        )

    def test_public_pages_render(self):
        for name in ['home', 'login', 'register']:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)


class PointLedgerTests(TestCase):
    def setUp(self):
        self.parent = CustomUser.objects.create_user(
            username='parent', password='pass12345', is_parent=True,
        )
        self.kid = CustomUser.objects.create_user(
            username='kid', password='pass12345', is_kid=True,
            parent_account=self.parent, notification_preference='none',
        )

    def test_penalty_below_zero_keeps_ledger_matching_balance(self):
        from .views import _award_points

        # Earn 5, then take a 10-point penalty: balance floors at 0, and the
        # ledger records only what was actually applied (-5), so the running
        # total a kid sees in their history still sums back to their balance.
        _award_points(self.kid, 5, 'behavior_positive', 'Tidied up')
        _award_points(self.kid, -10, 'penalty', 'Broke a window')

        self.kid.refresh_from_db()
        ledger = sum(t.amount for t in PointTransaction.objects.filter(user=self.kid))
        self.assertEqual(self.kid.points, 0)
        self.assertEqual(ledger, 0)
        self.assertEqual(self.kid.points, ledger)

    def test_normal_award_records_full_amount(self):
        from .views import _award_points

        _award_points(self.kid, 8, 'behavior_positive', 'Helped with dishes')

        self.kid.refresh_from_db()
        self.assertEqual(self.kid.points, 8)
        self.assertEqual(PointTransaction.objects.get(user=self.kid).amount, 8)


class FamilyCodeTests(TestCase):
    def _register(self, **extra):
        data = {
            'username': 'dad', 'first_name': 'Dad', 'last_name': 'X',
            'email': 'dad@example.com', 'avatar_color': '#6C63FF',
            'password': 'pass12345', 'confirm_password': 'pass12345',
        }
        data.update(extra)
        return self.client.post(reverse('register'), data)

    def setUp(self):
        self.mom = CustomUser.objects.create_user(username='mom', password='pass12345', is_parent=True)
        self.kid = CustomUser.objects.create_user(
            username='eva', password='pass12345', is_kid=True, parent_account=self.mom,
        )

    def test_every_user_gets_a_unique_family_code(self):
        self.assertEqual(len(self.mom.family_code), 6)
        self.assertNotEqual(self.mom.family_code, self.kid.family_code)

    def test_family_join_code_is_always_the_head_code(self):
        # Kid's shareable code resolves to the head parent's code.
        self.assertEqual(self.kid.family_join_code, self.mom.family_code)

    def test_partner_joins_existing_family_via_code(self):
        resp = self._register(join_family_code=self.mom.family_code.lower())  # case-insensitive
        self.assertRedirects(resp, reverse('dashboard'), fetch_redirect_response=False)
        dad = CustomUser.objects.get(username='dad')
        self.assertTrue(dad.is_parent)
        self.assertEqual(dad.parent_account_id, self.mom.id)
        self.assertEqual(dad.family_join_code, self.mom.family_code)
        # Co-parent sees the family's existing kid.
        self.assertIn(self.kid, list(dad.family_kids()))

    def test_invalid_family_code_is_rejected(self):
        resp = self._register(join_family_code='ZZZZZZ')
        self.assertEqual(resp.status_code, 200)  # re-rendered with error
        self.assertFalse(CustomUser.objects.filter(username='dad').exists())

    def test_blank_code_starts_a_new_family(self):
        resp = self._register()
        self.assertRedirects(resp, reverse('dashboard'), fetch_redirect_response=False)
        dad = CustomUser.objects.get(username='dad')
        self.assertIsNone(dad.parent_account_id)
        self.assertEqual(dad.family_head, dad)

    def test_coparent_can_review_task_created_by_other_parent(self):
        dad = CustomUser.objects.create_user(
            username='dad', password='pass12345', is_parent=True, parent_account=self.mom,
        )
        task = Task.objects.create(
            title='Dishes', parent=self.mom, assigned_to=self.kid,
            points_value=10, status='submitted', submitted_at=timezone.now(),
        )
        self.client.force_login(dad)
        resp = self.client.post(reverse('task_review', args=[task.pk]), {
            'action': 'approve', 'points_earned': 10, 'parent_feedback': 'great',
        })
        self.assertRedirects(resp, reverse('parent_dashboard'))
        self.kid.refresh_from_db()
        self.assertEqual(self.kid.points, 10)


class FullLifecycleIntegrationTests(TestCase):
    """Drive the whole product through the real web views, end to end, and prove
    the point ledger reconciles to the displayed balance at every step."""

    def _ledger(self, user):
        return sum(t.amount for t in PointTransaction.objects.filter(user=user))

    def test_register_assign_complete_approve_redeem_resolve(self):
        # 1. Parent self-registers (strong password required).
        resp = self.client.post(reverse('register'), {
            'username': 'momqa', 'first_name': 'Mom', 'last_name': 'Q',
            'email': 'momqa@example.com', 'avatar_color': '#6C63FF',
            'password': 'Tr0ub4dour!', 'confirm_password': 'Tr0ub4dour!',
        })
        self.assertRedirects(resp, reverse('dashboard'), fetch_redirect_response=False)
        parent = CustomUser.objects.get(username='momqa')
        self.assertTrue(parent.is_parent)

        # 2. Parent adds a kid (simple password allowed).
        resp = self.client.post(reverse('add_kid'), {
            'username': 'kidqa', 'first_name': 'Kid', 'avatar_color': '#4CAF50', 'password': '1234',
        })
        self.assertRedirects(resp, reverse('parent_dashboard'))
        kid = CustomUser.objects.get(username='kidqa')
        self.assertEqual(kid.parent_account_id, parent.id)

        # 3. Parent assigns a task.
        resp = self.client.post(reverse('task_create'), {
            'title': 'Dishes', 'description': '', 'assigned_to': kid.id,
            'category': 'chores', 'priority': 2, 'points_value': 20, 'preset': '',
        })
        self.assertRedirects(resp, reverse('task_list'))
        task = Task.objects.get(assigned_to=kid, title='Dishes')
        self.assertEqual(task.status, 'assigned')

        # 4. Kid logs in and submits the task.
        self.client.force_login(kid)
        resp = self.client.post(reverse('task_complete', args=[task.pk]), {
            'fun_rating': 4, 'effort_note': 'done',
        })
        self.assertRedirects(resp, reverse('kid_dashboard'))
        task.refresh_from_db()
        kid.refresh_from_db()
        self.assertEqual(task.status, 'submitted')
        self.assertEqual(kid.points, 0)  # not awarded until parent approves

        # 5. Parent approves with full points.
        self.client.force_login(parent)
        resp = self.client.post(reverse('task_review', args=[task.pk]), {
            'action': 'approve', 'points_earned': 20, 'parent_feedback': 'great',
        })
        self.assertRedirects(resp, reverse('parent_dashboard'))
        kid.refresh_from_db()
        self.assertEqual(kid.points, 20)
        self.assertEqual(self._ledger(kid), 20)  # ledger == balance

        # 6. Parent creates a reward the kid can afford.
        resp = self.client.post(reverse('reward_create'), {
            'title': 'Movie night', 'description': '', 'points_cost': 15,
            'icon': '🎬', 'is_active': 'on', 'preset': '',
        })
        self.assertRedirects(resp, reverse('reward_list'))
        reward = Reward.objects.get(parent=parent, title='Movie night')

        # 7. Kid redeems it (POST confirm).
        self.client.force_login(kid)
        resp = self.client.post(reverse('reward_redeem', args=[reward.pk]))
        self.assertRedirects(resp, reverse('kid_dashboard'))
        redemption = RewardRedemption.objects.get(kid=kid, reward=reward)
        self.assertEqual(redemption.status, 'pending')
        kid.refresh_from_db()
        self.assertEqual(kid.points, 20)  # nothing deducted until parent approves

        # 8. Parent approves the redemption (POST only).
        self.client.force_login(parent)
        resp = self.client.post(reverse('redemption_resolve', args=[redemption.pk, 'approve']))
        self.assertRedirects(resp, reverse('redemption_list'))
        redemption.refresh_from_db()
        kid.refresh_from_db()
        self.assertEqual(redemption.status, 'approved')
        self.assertEqual(kid.points, 5)            # 20 earned - 15 spent
        self.assertEqual(self._ledger(kid), 5)     # ledger still reconciles


class RegistrationValidationTests(TestCase):
    def _register(self, **extra):
        data = {
            'username': 'newdad', 'first_name': 'Dad', 'last_name': 'X',
            'email': 'newdad@example.com', 'avatar_color': '#6C63FF',
            'password': 'pass12345', 'confirm_password': 'pass12345',
        }
        data.update(extra)
        return self.client.post(reverse('register'), data)

    def test_parent_weak_password_is_rejected(self):
        # All-numeric + too short trips the configured validators.
        resp = self._register(password='123', confirm_password='123')
        self.assertEqual(resp.status_code, 200)  # re-rendered with errors
        self.assertFalse(CustomUser.objects.filter(username='newdad').exists())

    def test_parent_strong_password_is_accepted(self):
        resp = self._register(password='Tr0ub4dour!', confirm_password='Tr0ub4dour!')
        self.assertRedirects(resp, reverse('dashboard'), fetch_redirect_response=False)
        self.assertTrue(CustomUser.objects.filter(username='newdad', is_parent=True).exists())

    def test_kid_keeps_simple_password(self):
        # Kids are intentionally exempt from strength rules (parent picks it).
        parent = CustomUser.objects.create_user(username='p', password='pass12345', is_parent=True)
        self.client.force_login(parent)
        resp = self.client.post(reverse('add_kid'), {
            'username': 'lil', 'first_name': 'Lil', 'avatar_color': '#6C63FF', 'password': '123',
        })
        self.assertRedirects(resp, reverse('parent_dashboard'))
        self.assertTrue(CustomUser.objects.filter(username='lil', is_kid=True).exists())

    def test_taken_kid_username_suggests_alternative(self):
        CustomUser.objects.create_user(username='eva', password='pass12345', is_kid=True)
        parent = CustomUser.objects.create_user(username='p', password='pass12345', is_parent=True)
        self.client.force_login(parent)
        resp = self.client.post(reverse('add_kid'), {
            'username': 'eva', 'first_name': 'Eva', 'avatar_color': '#6C63FF', 'password': 'pass12345',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "eva2")  # suggested alternative

    def test_api_registration_ignores_role_and_requires_strong_password(self):
        # Weak password rejected.
        weak = self.client.post(reverse('api_register'), {
            'username': 'apidad', 'password': '123',
        })
        self.assertEqual(weak.status_code, 400)
        # Even if a client asks for is_kid, the public endpoint only makes parents.
        ok = self.client.post(reverse('api_register'), {
            'username': 'apidad', 'password': 'Tr0ub4dour!', 'is_kid': True, 'is_parent': False,
        })
        self.assertEqual(ok.status_code, 201)
        user = CustomUser.objects.get(username='apidad')
        self.assertTrue(user.is_parent)
        self.assertFalse(user.is_kid)
