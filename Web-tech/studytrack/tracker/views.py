import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.utils import timezone
from django.urls import reverse

from .models import Subject, Assignment
from .forms import SubjectForm, AssignmentForm, StudentRegistrationForm


def landing(request):
    """
    Public landing page introducing StudyTrack.
    Redirects authenticated students directly to their dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')


def register_view(request):
    """
    Student registration view using Django's User model and password hashing.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Registration successful! You can now log in with your credentials.'
            )
            return redirect('login')
    else:
        form = StudentRegistrationForm()

    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    """
    Student login view with clear authentication feedback.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.GET.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    else:
        form = AuthenticationForm(request)

    return render(request, 'registration/login.html', {'form': form})


def logout_view(request):
    """
    Student logout view. Accepts POST for secure state change, with GET fallback.
    """
    if request.method in ('POST', 'GET'):
        logout(request)
        messages.info(request, 'You have been successfully logged out.')
    return redirect('landing')


@login_required
def dashboard(request):
    """
    Student dashboard displaying real-time metrics, upcoming deadlines,
    and overdue warnings calculated directly from database records.
    """
    user = request.user
    today = timezone.localdate()

    # Base querysets scoped strictly to the authenticated student
    user_assignments = Assignment.objects.filter(user=user)
    total_assignments = user_assignments.count()
    completed_assignments = user_assignments.filter(status='completed').count()
    pending_assignments = user_assignments.filter(status='pending').count()
    
    # Overdue rule: strictly pending and due_date earlier than today
    # Completed assignments never count as overdue
    overdue_assignments_count = user_assignments.filter(
        status='pending',
        due_date__lt=today
    ).count()

    # Completion percentage
    if total_assignments > 0:
        completion_percentage = round((completed_assignments / total_assignments) * 100, 1)
    else:
        completion_percentage = 0.0

    # Upcoming deadlines (pending assignments due today or later, nearest first)
    upcoming_deadlines = user_assignments.filter(
        status='pending',
        due_date__gte=today
    ).select_related('subject').order_by('due_date')[:5]

    # Overdue items for the alert list
    overdue_list = user_assignments.filter(
        status='pending',
        due_date__lt=today
    ).select_related('subject').order_by('due_date')[:5]

    subjects_count = Subject.objects.filter(user=user).count()

    context = {
        'total_assignments': total_assignments,
        'completed_assignments': completed_assignments,
        'pending_assignments': pending_assignments,
        'overdue_assignments': overdue_assignments_count,
        'completion_percentage': completion_percentage,
        'upcoming_deadlines': upcoming_deadlines,
        'overdue_list': overdue_list,
        'subjects_count': subjects_count,
        'today': today,
    }
    return render(request, 'tracker/dashboard.html', context)


@login_required
def assignment_list(request):
    """
    List assignments with combined search and filtering (subject, status, priority),
    sorted by nearest deadline first.
    """
    user = request.user
    today = timezone.localdate()
    assignments = Assignment.objects.filter(user=user).select_related('subject')

    # Query parameters
    search_query = request.GET.get('q', '').strip()
    selected_subject = request.GET.get('subject', '').strip()
    selected_status = request.GET.get('status', '').strip()
    selected_priority = request.GET.get('priority', '').strip()

    # Apply search filter
    if search_query:
        assignments = assignments.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Apply subject filter (validate ownership)
    if selected_subject and selected_subject.isdigit():
        assignments = assignments.filter(subject_id=int(selected_subject))

    # Apply status filter
    if selected_status in ('pending', 'completed'):
        assignments = assignments.filter(status=selected_status)

    # Apply priority filter
    if selected_priority in ('low', 'medium', 'high'):
        assignments = assignments.filter(priority=selected_priority)

    # Sorting: nearest deadline first
    assignments = assignments.order_by('due_date', 'title')

    # Available subjects for dropdown
    subjects = Subject.objects.filter(user=user).order_by('name')

    # Check if any filter is actively applied
    has_active_filters = bool(
        search_query or
        (selected_subject and selected_subject.isdigit()) or
        (selected_status in ('pending', 'completed')) or
        (selected_priority in ('low', 'medium', 'high'))
    )

    context = {
        'assignments': assignments,
        'subjects': subjects,
        'search_query': search_query,
        'selected_subject': selected_subject,
        'selected_status': selected_status,
        'selected_priority': selected_priority,
        'has_active_filters': has_active_filters,
        'today': today,
        'total_results': assignments.count(),
    }
    return render(request, 'tracker/assignment_list.html', context)


@login_required
def assignment_create(request):
    """
    Create a new assignment. Ensures the selected subject belongs to the current user.
    """
    user = request.user
    user_subjects = Subject.objects.filter(user=user)

    if not user_subjects.exists():
        messages.warning(
            request,
            'You must create at least one subject before adding assignments.'
        )
        return redirect('subject_create')

    if request.method == 'POST':
        form = AssignmentForm(user, request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.user = user
            assignment.save()
            messages.success(request, f'Assignment "{assignment.title}" created successfully.')
            return redirect('assignment_list')
    else:
        # Preselect subject if passed via GET query
        initial = {}
        sub_id = request.GET.get('subject')
        if sub_id and sub_id.isdigit():
            initial['subject'] = sub_id
        form = AssignmentForm(user, initial=initial)

    return render(request, 'tracker/assignment_form.html', {
        'form': form,
        'is_edit': False,
    })


@login_required
def assignment_update(request, pk):
    """
    Edit an existing assignment owned by the current student.
    """
    assignment = get_object_or_404(Assignment, pk=pk, user=request.user)

    if request.method == 'POST':
        form = AssignmentForm(request.user, request.POST, instance=assignment)
        if form.is_valid():
            form.save()
            messages.success(request, f'Assignment "{assignment.title}" updated successfully.')
            return redirect('assignment_list')
    else:
        form = AssignmentForm(request.user, instance=assignment)

    return render(request, 'tracker/assignment_form.html', {
        'form': form,
        'assignment': assignment,
        'is_edit': True,
    })


@login_required
def assignment_delete(request, pk):
    """
    Delete an assignment owned by the current student after confirmation.
    Must be a POST request to mutate state.
    """
    assignment = get_object_or_404(Assignment, pk=pk, user=request.user)

    if request.method == 'POST':
        title = assignment.title
        assignment.delete()
        messages.success(request, f'Assignment "{title}" has been deleted.')
        return redirect('assignment_list')

    return render(request, 'tracker/assignment_confirm_delete.html', {
        'assignment': assignment,
    })


@login_required
def assignment_toggle_status(request, pk):
    """
    Toggle assignment completion status between 'pending' and 'completed'.
    Only accepts POST requests. Supports both standard form POST and AJAX fetch().
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    assignment = get_object_or_404(Assignment, pk=pk, user=request.user)

    if assignment.status == 'completed':
        assignment.status = 'pending'
    else:
        assignment.status = 'completed'

    assignment.save()

    # Check if request is an AJAX call
    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('accept', '')
    )

    if is_ajax:
        return JsonResponse({
            'success': True,
            'id': assignment.id,
            'new_status': assignment.status,
            'status_display': assignment.get_status_display(),
            'is_completed': assignment.status == 'completed',
            'is_overdue': assignment.is_overdue,
        })

    messages.success(
        request,
        f'Assignment "{assignment.title}" marked as {assignment.get_status_display().lower()}.'
    )
    # Redirect back to referring page or assignment list
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('assignment_list')
    return redirect(next_url)


@login_required
def subject_list(request):
    """
    List student's subjects with their respective assignment counts.
    """
    subjects = Subject.objects.filter(user=request.user).annotate(
        assignment_count=Count('assignments')
    ).order_by('name')

    return render(request, 'tracker/subject_list.html', {
        'subjects': subjects,
    })


@login_required
def subject_create(request):
    """
    Create a new subject for the authenticated student.
    """
    if request.method == 'POST':
        form = SubjectForm(request.user, request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.user = request.user
            subject.save()
            messages.success(request, f'Subject "{subject.name}" added successfully.')
            return redirect('subject_list')
    else:
        form = SubjectForm(request.user)

    return render(request, 'tracker/subject_form.html', {
        'form': form,
        'is_edit': False,
    })


@login_required
def subject_update(request, pk):
    """
    Edit an existing subject owned by the authenticated student.
    """
    subject = get_object_or_404(Subject, pk=pk, user=request.user)

    if request.method == 'POST':
        form = SubjectForm(request.user, request.POST, instance=subject)
        if form.is_valid():
            form.save()
            messages.success(request, f'Subject "{subject.name}" updated successfully.')
            return redirect('subject_list')
    else:
        form = SubjectForm(request.user, instance=subject)

    return render(request, 'tracker/subject_form.html', {
        'form': form,
        'subject': subject,
        'is_edit': True,
    })


@login_required
def subject_delete(request, pk):
    """
    Delete a subject owned by the current student.
    Integrity rule: If the subject has assignments, block deletion and instruct
    the student to first reassign or delete those assignments.
    """
    subject = get_object_or_404(Subject, pk=pk, user=request.user)
    assignment_count = subject.assignments.count()

    if assignment_count > 0:
        messages.error(
            request,
            f'Cannot delete subject "{subject.name}" because it still has {assignment_count} assignment(s) linked to it. '
            'Please delete or reassign those assignments first.'
        )
        return redirect('subject_list')

    if request.method == 'POST':
        name = subject.name
        subject.delete()
        messages.success(request, f'Subject "{name}" has been deleted.')
        return redirect('subject_list')

    return render(request, 'tracker/subject_confirm_delete.html', {
        'subject': subject,
    })


@login_required
def export_assignments_csv(request):
    """
    Optional enhancement: Export all assignments of the authenticated student to a CSV file.
    """
    user = request.user
    assignments = Assignment.objects.filter(user=user).select_related('subject').order_by('due_date')

    response = HttpResponse(content_type='text/csv')
    filename = f"studytrack_assignments_{timezone.localdate()}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Title', 'Subject', 'Course Code', 'Due Date', 'Priority', 'Status', 'Overdue'])

    for item in assignments:
        writer.writerow([
            item.title,
            item.subject.name,
            item.subject.course_code or '',
            item.due_date,
            item.get_priority_display(),
            item.get_status_display(),
            'Yes' if item.is_overdue else 'No',
        ])

    return response
