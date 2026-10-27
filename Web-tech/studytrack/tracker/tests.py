from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Subject, Assignment
from .forms import SubjectForm, AssignmentForm, StudentRegistrationForm


class SecurityAndAuthTests(TestCase):
    """
    Test authentication requirements and route protection.
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='student1', password='password123')
        self.subject = Subject.objects.create(user=self.user, name='Computer Networks', course_code='CS301')
        self.assignment = Assignment.objects.create(
            user=self.user,
            subject=self.subject,
            title='Socket Programming Lab',
            due_date=timezone.localdate() + timedelta(days=2),
            priority='high',
            status='pending'
        )

    def test_anonymous_redirect_from_private_views(self):
        """Anonymous requests to private endpoints must redirect to login."""
        private_urls = [
            reverse('dashboard'),
            reverse('assignment_list'),
            reverse('assignment_create'),
            reverse('assignment_update', kwargs={'pk': self.assignment.id}),
            reverse('assignment_delete', kwargs={'pk': self.assignment.id}),
            reverse('subject_list'),
            reverse('subject_create'),
            reverse('subject_update', kwargs={'pk': self.subject.id}),
            reverse('subject_delete', kwargs={'pk': self.subject.id}),
        ]
        for url in private_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('login'), response.url)

    def test_registration_and_login_flow(self):
        """New student can register, login, and access dashboard."""
        reg_response = self.client.post(reverse('register'), {
            'username': 'newstudent',
            'email': 'newstudent@example.edu',
            'password': 'safePassword123',
            'confirm_password': 'safePassword123',
        })
        self.assertEqual(reg_response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newstudent').exists())

        login_response = self.client.post(reverse('login'), {
            'username': 'newstudent',
            'password': 'safePassword123',
        })
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(login_response.url, reverse('dashboard'))


class OwnershipAndAuthorizationTests(TestCase):
    """
    Ensure User A cannot view, mutate, complete, or delete User B's records.
    """
    def setUp(self):
        self.user_a = User.objects.create_user(username='studentA', password='password123')
        self.user_b = User.objects.create_user(username='studentB', password='password123')

        self.subject_a = Subject.objects.create(user=self.user_a, name='Web Tech', course_code='AIM3140')
        self.subject_b = Subject.objects.create(user=self.user_b, name='Operating Systems', course_code='CS302')

        self.assignment_a = Assignment.objects.create(
            user=self.user_a,
            subject=self.subject_a,
            title='Django MVT Assignment',
            due_date=timezone.localdate() + timedelta(days=3),
            priority='high',
            status='pending'
        )
        self.assignment_b = Assignment.objects.create(
            user=self.user_b,
            subject=self.subject_b,
            title='Linux Kernel Module',
            due_date=timezone.localdate() + timedelta(days=5),
            priority='medium',
            status='pending'
        )

    def test_user_cannot_access_or_edit_another_users_assignment(self):
        """User A attempting to access User B's assignment must receive 404."""
        self.client.login(username='studentA', password='password123')

        # GET update page
        res_get = self.client.get(reverse('assignment_update', kwargs={'pk': self.assignment_b.id}))
        self.assertEqual(res_get.status_code, 404)

        # POST update
        res_post = self.client.post(reverse('assignment_update', kwargs={'pk': self.assignment_b.id}), {
            'title': 'Hacked Title',
            'subject': self.subject_b.id,
            'due_date': str(timezone.localdate()),
            'priority': 'low',
            'status': 'completed',
        })
        self.assertEqual(res_post.status_code, 404)
        self.assignment_b.refresh_from_db()
        self.assertEqual(self.assignment_b.title, 'Linux Kernel Module')

    def test_user_cannot_delete_another_users_assignment(self):
        """User A attempting to delete User B's assignment must receive 404."""
        self.client.login(username='studentA', password='password123')
        res_del = self.client.post(reverse('assignment_delete', kwargs={'pk': self.assignment_b.id}))
        self.assertEqual(res_del.status_code, 404)
        self.assertTrue(Assignment.objects.filter(id=self.assignment_b.id).exists())

    def test_user_cannot_toggle_another_users_assignment_status(self):
        """User A attempting to toggle User B's assignment must receive 404."""
        self.client.login(username='studentA', password='password123')
        res_toggle = self.client.post(reverse('assignment_toggle_status', kwargs={'pk': self.assignment_b.id}))
        self.assertEqual(res_toggle.status_code, 404)
        self.assignment_b.refresh_from_db()
        self.assertEqual(self.assignment_b.status, 'pending')

    def test_user_cannot_assign_to_another_users_subject(self):
        """User A cannot create or update an assignment linked to User B's subject."""
        # 1. Model layer validation
        invalid_assignment = Assignment(
            user=self.user_a,
            subject=self.subject_b,  # belongs to User B!
            title='Malicious Link',
            due_date=timezone.localdate() + timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            invalid_assignment.full_clean()

        # 2. Form layer validation
        form = AssignmentForm(self.user_a, data={
            'title': 'Cross User Test',
            'subject': self.subject_b.id,
            'due_date': str(timezone.localdate() + timedelta(days=1)),
            'priority': 'medium',
            'status': 'pending',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('subject', form.errors)


class SubjectIntegrityAndDeletionTests(TestCase):
    """
    Test subject CRUD and block-deletion integrity rules.
    """
    def setUp(self):
        self.user = User.objects.create_user(username='student', password='password123')
        self.subject = Subject.objects.create(user=self.user, name='Data Structures', course_code='CS201')
        self.client = Client()
        self.client.login(username='student', password='password123')

    def test_subject_deletion_blocked_when_assignments_exist(self):
        """Subject with active assignments cannot be deleted."""
        Assignment.objects.create(
            user=self.user,
            subject=self.subject,
            title='Binary Search Trees Lab',
            due_date=timezone.localdate() + timedelta(days=2),
        )
        response = self.client.post(reverse('subject_delete', kwargs={'pk': self.subject.id}))
        self.assertEqual(response.status_code, 302)
        # Verify subject still exists in database
        self.assertTrue(Subject.objects.filter(id=self.subject.id).exists())

    def test_subject_deletion_allowed_when_empty(self):
        """Subject with 0 assignments can be deleted."""
        response = self.client.post(reverse('subject_delete', kwargs={'pk': self.subject.id}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Subject.objects.filter(id=self.subject.id).exists())


class DashboardMetricsCalculationsTests(TestCase):
    """
    Test exact calculation rules for dashboard metrics:
    - total, pending, completed, overdue, completion_percentage
    - Boundary rule: completed assignments are NEVER overdue.
    - Zero division safety.
    """
    def setUp(self):
        self.user = User.objects.create_user(username='math_student', password='password123')
        self.subject = Subject.objects.create(user=self.user, name='Discrete Mathematics')
        self.client = Client()
        self.client.login(username='math_student', password='password123')
        self.today = timezone.localdate()

    def test_zero_assignments_metrics(self):
        """Zero assignments must produce 0 metrics with no division-by-zero errors."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_assignments'], 0)
        self.assertEqual(response.context['pending_assignments'], 0)
        self.assertEqual(response.context['completed_assignments'], 0)
        self.assertEqual(response.context['overdue_assignments'], 0)
        self.assertEqual(response.context['completion_percentage'], 0.0)

    def test_overdue_and_completed_past_due_calculations(self):
        """
        - 1 pending due yesterday -> OVERDUE
        - 1 pending due tomorrow -> PENDING, NOT OVERDUE
        - 1 completed due yesterday -> COMPLETED, NEVER OVERDUE
        - 1 completed due today -> COMPLETED
        Total = 4, Completed = 2, Pending = 2, Overdue = 1, Percentage = 50.0%
        """
        # 1. Overdue pending item
        Assignment.objects.create(
            user=self.user,
            subject=self.subject,
            title='Task Overdue Yesterday',
            due_date=self.today - timedelta(days=1),
            status='pending'
        )
        # 2. Upcoming pending item
        Assignment.objects.create(
            user=self.user,
            subject=self.subject,
            title='Task Due Tomorrow',
            due_date=self.today + timedelta(days=1),
            status='pending'
        )
        # 3. Past-due completed item (must NEVER count as overdue)
        Assignment.objects.create(
            user=self.user,
            subject=self.subject,
            title='Task Completed Past Due',
            due_date=self.today - timedelta(days=3),
            status='completed'
        )
        # 4. Completed item due today
        Assignment.objects.create(
            user=self.user,
            subject=self.subject,
            title='Task Completed Today',
            due_date=self.today,
            status='completed'
        )

        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_assignments'], 4)
        self.assertEqual(response.context['completed_assignments'], 2)
        self.assertEqual(response.context['pending_assignments'], 2)
        self.assertEqual(response.context['overdue_assignments'], 1)
        self.assertEqual(response.context['completion_percentage'], 50.0)


class SearchAndFilterTests(TestCase):
    """
    Test assignment search, multiple combined filters, and invalid filter safety.
    """
    def setUp(self):
        self.user = User.objects.create_user(username='filter_user', password='password123')
        self.client = Client()
        self.client.login(username='filter_user', password='password123')

        self.sub1 = Subject.objects.create(user=self.user, name='Artificial Intelligence', course_code='AI401')
        self.sub2 = Subject.objects.create(user=self.user, name='Database Systems', course_code='CS303')

        today = timezone.localdate()
        self.a1 = Assignment.objects.create(
            user=self.user, subject=self.sub1, title='A* Search Algorithm',
            due_date=today + timedelta(days=1), priority='high', status='pending'
        )
        self.a2 = Assignment.objects.create(
            user=self.user, subject=self.sub1, title='Neural Network Perceptron',
            due_date=today + timedelta(days=5), priority='medium', status='completed'
        )
        self.a3 = Assignment.objects.create(
            user=self.user, subject=self.sub2, title='SQL Relational Calculus',
            due_date=today + timedelta(days=2), priority='high', status='pending'
        )

    def test_search_by_title_and_description(self):
        res = self.client.get(reverse('assignment_list'), {'q': 'Search Algorithm'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context['assignments']), 1)
        self.assertEqual(res.context['assignments'][0].id, self.a1.id)

    def test_combined_filters(self):
        """Filter by Subject=sub1 AND Priority=high AND Status=pending."""
        res = self.client.get(reverse('assignment_list'), {
            'subject': self.sub1.id,
            'priority': 'high',
            'status': 'pending',
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context['assignments']), 1)
        self.assertEqual(res.context['assignments'][0].id, self.a1.id)

    def test_invalid_filter_safety(self):
        """Invalid filter parameters must be ignored gracefully without error."""
        res = self.client.get(reverse('assignment_list'), {
            'status': 'INVALID_STATUS',
            'priority': 'MALICIOUS_CHOICE',
            'subject': 'NOT_A_NUMBER',
        })
        self.assertEqual(res.status_code, 200)
        # Should fall back to returning all 3 assignments for this user
        self.assertEqual(len(res.context['assignments']), 3)


class StateChangesAndCSRFTests(TestCase):
    """
    Verify state-changing operations require POST and handle AJAX/standard flows.
    """
    def setUp(self):
        self.user = User.objects.create_user(username='state_user', password='password123')
        self.subject = Subject.objects.create(user=self.user, name='Software Engineering')
        self.assignment = Assignment.objects.create(
            user=self.user,
            subject=self.subject,
            title='UML Class Diagram',
            due_date=timezone.localdate() + timedelta(days=1),
            status='pending'
        )
        self.client = Client()
        self.client.login(username='state_user', password='password123')

    def test_toggle_status_rejects_get(self):
        """Status toggle must disallow GET requests."""
        res = self.client.get(reverse('assignment_toggle_status', kwargs={'pk': self.assignment.id}))
        self.assertEqual(res.status_code, 405)

    def test_toggle_status_via_post_and_ajax(self):
        """Toggle status switches between pending and completed."""
        # Standard POST
        res_post = self.client.post(reverse('assignment_toggle_status', kwargs={'pk': self.assignment.id}))
        self.assertEqual(res_post.status_code, 302)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, 'completed')

        # AJAX POST
        res_ajax = self.client.post(
            reverse('assignment_toggle_status', kwargs={'pk': self.assignment.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(res_ajax.status_code, 200)
        data = res_ajax.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['new_status'], 'pending')
        self.assertFalse(data['is_completed'])
