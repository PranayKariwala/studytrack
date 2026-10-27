"""
StudyTrack Demo Data Seeder
Populates realistic academic demo records for presentation & testing.
Run via: python seed_demo_data.py
"""

import os
import sys
from datetime import timedelta
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from tracker.models import Subject, Assignment


def seed():
    print("Seeding StudyTrack demo data...")
    today = timezone.localdate()

    # Create demo students
    user1, _ = User.objects.get_or_create(username='rahul_cse', defaults={'email': 'rahul@student.edu'})
    user1.set_password('student123')
    user1.save()

    user2, _ = User.objects.get_or_create(username='priya_aiml', defaults={'email': 'priya@student.edu'})
    user2.set_password('student123')
    user2.save()

    print(f"Created student accounts: 'rahul_cse' (pwd: student123) and 'priya_aiml' (pwd: student123)")

    # Create Subjects for User 1 (Rahul)
    sub_wt, _ = Subject.objects.get_or_create(user=user1, name='Web Technologies', defaults={'course_code': 'AIM3140'})
    sub_os, _ = Subject.objects.get_or_create(user=user1, name='Operating Systems', defaults={'course_code': 'CS302'})
    sub_ml, _ = Subject.objects.get_or_create(user=user1, name='Machine Learning', defaults={'course_code': 'AI304'})

    # Create Subjects for User 2 (Priya)
    sub_db, _ = Subject.objects.get_or_create(user=user2, name='Database Systems', defaults={'course_code': 'CS303'})

    # Create Rahul's Assignments
    assignments_data = [
        {
            'user': user1,
            'subject': sub_wt,
            'title': 'StudyTrack Django MVT & MySQL Mini Project',
            'description': 'Implement authentication, CRUD views, templates, and ownership authorization.',
            'due_date': today + timedelta(days=2),
            'priority': 'high',
            'status': 'pending',
        },
        {
            'user': user1,
            'subject': sub_os,
            'title': 'Deadlock Avoidance Banker\'s Algorithm Simulation',
            'description': 'Write a Python simulation of Banker\'s algorithm for resource allocation.',
            'due_date': today - timedelta(days=2),  # OVERDUE!
            'priority': 'high',
            'status': 'pending',
        },
        {
            'user': user1,
            'subject': sub_ml,
            'title': 'Linear Regression & Cost Function Gradient Descent',
            'description': 'Jupyter notebook analyzing dataset loss convergence curves.',
            'due_date': today - timedelta(days=5),  # Completed past-due
            'priority': 'medium',
            'status': 'completed',
        },
        {
            'user': user1,
            'subject': sub_wt,
            'title': 'CSS Flexbox & Bootstrap 5 Responsive Grid Design',
            'description': 'Mobile-friendly navigation and cards UI.',
            'due_date': today + timedelta(days=6),
            'priority': 'low',
            'status': 'pending',
        },
    ]

    for item in assignments_data:
        assignment, created = Assignment.objects.get_or_create(
            user=item['user'],
            title=item['title'],
            defaults=item
        )
        if not created:
            for k, v in item.items():
                setattr(assignment, k, v)
            assignment.save()

    # Create Priya's Assignment
    Assignment.objects.get_or_create(
        user=user2,
        title='SQL B-Tree Indexing Optimization',
        defaults={
            'subject': sub_db,
            'description': 'Analyze query execution plans with EXPLAIN.',
            'due_date': today + timedelta(days=4),
            'priority': 'high',
            'status': 'pending',
        }
    )

    print("Demo data seeded successfully!")
    print("Summary for 'rahul_cse':")
    print(f"- Total Assignments: {user1.assignments.count()}")
    print(f"- Pending: {user1.assignments.filter(status='pending').count()}")
    print(f"- Completed: {user1.assignments.filter(status='completed').count()}")
    print(f"- Overdue: {user1.assignments.filter(status='pending', due_date__lt=today).count()}")


if __name__ == '__main__':
    seed()
