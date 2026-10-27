from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Subject, Assignment


class SubjectForm(forms.ModelForm):
    """
    Form for creating and updating subjects owned by the current student.
    """
    class Meta:
        model = Subject
        fields = ['name', 'course_code']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Web Technologies',
                'required': True,
                'id': 'id_subject_name',
            }),
            'course_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. AIM3140 (optional)',
                'id': 'id_course_code',
            }),
        }

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError('Subject name is required and cannot be blank.')
        
        # Prevent accidental duplicate subject name for the same student
        existing = Subject.objects.filter(user=self.user, name__iexact=name)
        if self.instance and self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise ValidationError('You already have a subject with this name.')
        return name

    def clean_course_code(self):
        code = self.cleaned_data.get('course_code')
        if code:
            code = code.strip()
        return code or None


class AssignmentForm(forms.ModelForm):
    """
    Form for creating and editing assignments, strictly scoped to the student's subjects.
    """
    class Meta:
        model = Assignment
        fields = ['title', 'subject', 'description', 'due_date', 'priority', 'status']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Implement Django MVT Architecture',
                'required': True,
                'id': 'id_assignment_title',
            }),
            'subject': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
                'id': 'id_assignment_subject',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional details, references, or instructions...',
                'id': 'id_assignment_description',
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
                'id': 'id_assignment_due_date',
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_assignment_priority',
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_assignment_status',
            }),
        }

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        # Scope available subjects ONLY to the current user's subjects
        self.fields['subject'].queryset = Subject.objects.filter(user=user)
        self.fields['subject'].empty_label = '--- Select a Subject ---'

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise ValidationError('Assignment title is required and cannot be blank.')
        return title

    def clean_subject(self):
        subject = self.cleaned_data.get('subject')
        if not subject:
            raise ValidationError('Please select a valid subject.')
        # Cross-user authorization check
        if subject.user_id != self.user.id:
            raise ValidationError('The selected subject does not belong to your account.')
        return subject

    def clean(self):
        cleaned_data = super().clean()
        subject = cleaned_data.get('subject')
        if subject and subject.user_id != self.user.id:
            self.add_error('subject', 'Security violation: Cannot link assignment to another user\'s subject.')
        return cleaned_data


class StudentRegistrationForm(forms.ModelForm):
    """
    Form for registering a new student account using Django auth with validation.
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a password (min. 6 characters)',
            'required': True,
            'id': 'id_reg_password',
        }),
        min_length=6,
        help_text='Password must be at least 6 characters.'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'required': True,
            'id': 'id_reg_confirm_password',
        }),
        help_text='Re-type the exact same password.'
    )

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username',
                'required': True,
                'id': 'id_reg_username',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Student email address (optional)',
                'id': 'id_reg_email',
            }),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise ValidationError('Username cannot be blank.')
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('This username is already taken. Please choose another.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match. Please re-enter.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user
