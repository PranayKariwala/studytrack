from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone


class Subject(models.Model):
    """
    Academic subject belonging to a specific student user.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subjects',
        help_text="The student owner of this subject."
    )
    name = models.CharField(
        max_length=100,
        help_text="Name of the subject (e.g., Web Technologies)."
    )
    course_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Optional course or subject code (e.g., AIM3140)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ('user', 'name')
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'

    def clean(self):
        super().clean()
        if self.name:
            self.name = self.name.strip()
            if not self.name:
                raise ValidationError({'name': 'Subject name cannot be blank.'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.course_code:
            return f"{self.name} ({self.course_code})"
        return self.name


class Assignment(models.Model):
    """
    Assignment task belonging to a student user and linked to one of their subjects.
    """
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assignments',
        help_text="The student owner of this assignment."
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='assignments',
        help_text="The subject this assignment belongs to."
    )
    title = models.CharField(
        max_length=200,
        help_text="Title or brief description of the assignment."
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text="Optional detailed instructions, rubrics, or notes."
    )
    due_date = models.DateField(
        help_text="Due date for assignment submission (YYYY-MM-DD)."
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        help_text="Priority level: low, medium, or high."
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Status: pending or completed."
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the assignment was marked as completed."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', 'title']
        indexes = [
            models.Index(fields=['user', 'status', 'due_date']),
        ]
        verbose_name = 'Assignment'
        verbose_name_plural = 'Assignments'

    def clean(self):
        super().clean()
        if self.title:
            self.title = self.title.strip()
            if not self.title:
                raise ValidationError({'title': 'Assignment title cannot be blank.'})

        # Cross-user integrity check: Assignment owner must match Subject owner
        if self.subject_id and self.user_id:
            if self.subject.user_id != self.user_id:
                raise ValidationError({
                    'subject': 'The selected subject does not belong to your account.'
                })

    def save(self, *args, **kwargs):
        self.clean()
        # Maintain completed_at timestamp automatically based on status
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status == 'pending':
            self.completed_at = None
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """
        Calculates overdue state:
        Only pending assignments whose due date is strictly earlier than today's local date.
        Completed assignments are never overdue.
        """
        if self.status != 'pending' or not self.due_date:
            return False
        return self.due_date < timezone.localdate()

    def __str__(self):
        return f"{self.title} - {self.subject.name} (Due: {self.due_date})"
