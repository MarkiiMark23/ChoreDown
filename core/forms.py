from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomUser, Task, Behavior, Reward

AVATAR_COLORS = [
    ('#6C63FF', 'Purple'),
    ('#F7557A', 'Pink'),
    ('#FF9800', 'Orange'),
    ('#4CAF50', 'Green'),
    ('#2196F3', 'Blue'),
    ('#FF5722', 'Red'),
    ('#009688', 'Teal'),
    ('#9C27B0', 'Violet'),
]

REWARD_ICONS = [
    ('🎮', 'Video Game'),
    ('🎬', 'Movie'),
    ('🍕', 'Pizza'),
    ('🍦', 'Ice Cream'),
    ('🎁', 'Gift'),
    ('💰', 'Money'),
    ('🏖️', 'Trip'),
    ('🎉', 'Party'),
    ('📱', 'Screen Time'),
    ('🛒', 'Shopping'),
    ('🎠', 'Theme Park'),
    ('⭐', 'Star'),
]


class ParentRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))
    avatar_color = forms.ChoiceField(choices=AVATAR_COLORS, widget=forms.RadioSelect)

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'avatar_color']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Username'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email'}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('confirm_password'):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.is_parent = True
        if commit:
            user.save()
        return user


class AddKidForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'}),
        help_text="Create a simple password the kid can remember."
    )
    avatar_color = forms.ChoiceField(choices=AVATAR_COLORS, widget=forms.RadioSelect)

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'avatar_color']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Username (e.g. eva_2014)'}),
            'first_name': forms.TextInput(attrs={'placeholder': "Kid's first name"}),
        }

    def save(self, parent, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.is_kid = True
        user.parent_account = parent
        if commit:
            user.save()
        return user


class TaskCreateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'assigned_to', 'category', 'priority', 'points_value', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Task title'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional details...'}),
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'points_value': forms.NumberInput(attrs={'min': 1, 'max': 100}),
        }

    def __init__(self, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_to'].queryset = parent.children.filter(is_kid=True)
        self.fields['assigned_to'].empty_label = "Select a kid"


class BehaviorLogForm(forms.ModelForm):
    class Meta:
        model = Behavior
        fields = ['associated_with', 'behavior_type', 'description', 'points_value']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'What happened?'}),
            'points_value': forms.NumberInput(attrs={'min': 1, 'max': 50}),
        }

    def __init__(self, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['associated_with'].queryset = parent.children.filter(is_kid=True)
        self.fields['associated_with'].empty_label = "Select a kid"


class RewardCreateForm(forms.ModelForm):
    icon = forms.ChoiceField(choices=REWARD_ICONS, widget=forms.RadioSelect)

    class Meta:
        model = Reward
        fields = ['title', 'description', 'points_cost', 'icon', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Extra screen time'}),
            'description': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional details...'}),
            'points_cost': forms.NumberInput(attrs={'min': 1}),
        }


class TaskCompleteForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['fun_rating', 'did_not_finish', 'not_quite']
        widgets = {
            'fun_rating': forms.RadioSelect,
        }
