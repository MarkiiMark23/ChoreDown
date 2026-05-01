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
    ('🌙', 'Stay Up Late'),
    ('⭐', 'Star'),
]

TASK_PRESETS = {
    'clean_room': {
        'label': 'Clean room',
        'title': 'Clean your room',
        'category': 'chores',
        'points': 15,
        'description': 'Pick up clothes, clear trash, and reset the bed.',
    },
    'brush_teeth': {
        'label': 'Brush teeth',
        'title': 'Brush teeth',
        'category': 'hygiene',
        'points': 5,
        'description': 'Brush for two minutes and rinse.',
    },
    'homework': {
        'label': 'Homework',
        'title': 'Finish homework',
        'category': 'homework',
        'points': 20,
        'description': 'Complete the assigned homework and pack it away.',
    },
    'read': {
        'label': 'Read',
        'title': 'Read for 20 minutes',
        'category': 'homework',
        'points': 10,
        'description': 'Read quietly and mark your stopping place.',
    },
    'dishes': {
        'label': 'Dishes',
        'title': 'Help with dishes',
        'category': 'chores',
        'points': 10,
        'description': 'Clear dishes and help load or unload the dishwasher.',
    },
    'laundry': {
        'label': 'Laundry',
        'title': 'Put away laundry',
        'category': 'chores',
        'points': 12,
        'description': 'Put clean clothes where they belong.',
    },
    'trash': {
        'label': 'Take out trash',
        'title': 'Take out trash',
        'category': 'chores',
        'points': 10,
        'description': 'Tie the bag, take it out, and replace the liner.',
    },
    'pet_care': {
        'label': 'Pet care',
        'title': 'Pet care',
        'category': 'chores',
        'points': 10,
        'description': 'Check food, water, and the pet area.',
    },
    'backpack': {
        'label': 'Backpack reset',
        'title': 'Reset backpack',
        'category': 'homework',
        'points': 8,
        'description': 'Pack homework, folders, lunch items, and supplies.',
    },
    'bedtime': {
        'label': 'Bedtime routine',
        'title': 'Bedtime routine',
        'category': 'hygiene',
        'points': 12,
        'description': 'Pajamas, teeth, bathroom, and clothes ready for tomorrow.',
    },
}

REWARD_PRESETS = {
    'screen_time': ('Extra screen time', '1 extra hour of screen time.', 30, '📱'),
    'game_time': ('Game time', '30 extra minutes gaming.', 35, '🎮'),
    'movie_pick': ('Movie night pick', 'Choose the movie for family movie night.', 50, '🎬'),
    'snack': ('Special snack', 'Pick a favorite snack or treat.', 20, '🍦'),
    'allowance': ('Allowance bonus', 'Small allowance bonus approved by parent.', 50, '💰'),
    'outing': ('Special outing', 'Pick a park, library, or activity outing.', 80, '🏖️'),
    'stay_up_late': ('Stay up late', 'Stay up 30 minutes later on an approved night.', 40, '🌙'),
    'choose_dinner': ('Choose dinner', 'Choose dinner for the family.', 60, '🍕'),
    'toy_book': ('Toy or book', 'Pick a small toy, book, or activity item.', 75, '🎁'),
    'special_activity': ('Special activity', 'Choose a parent-approved activity.', 65, '🎉'),
}

BEHAVIOR_PRESETS = {
    'helped': ('positive', 'Helped without being asked', 10),
    'kind_words': ('positive', 'Used kind words during a hard moment', 8),
    'focus_streak': ('positive', 'Stayed with a focus task', 10),
    'morning_routine': ('positive', 'Completed morning routine with fewer reminders', 10),
    'arguing': ('negative', 'Had a hard time with arguing', 8),
    'unsafe': ('negative', 'Unsafe choice that needs a reset', 15),
    'disrespect': ('negative', 'Disrespectful words or tone', 8),
    'missed_routine': ('negative', 'Missed an agreed routine step', 5),
    'repeated_reminders': ('negative', 'Needed repeated reminders after support', 5),
}


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
    preset = forms.ChoiceField(
        choices=[('', 'Custom task')] + [(key, data['label']) for key, data in TASK_PRESETS.items()],
        required=False,
    )

    class Meta:
        model = Task
        fields = ['title', 'description', 'assigned_to', 'category', 'priority', 'points_value', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Task title'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional details...'}),
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'points_value': forms.NumberInput(attrs={'min': 1, 'max': 100}),
        }
        labels = {
            'due_date': 'When? (Optional)',
        }

    def __init__(self, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        kids = parent.children.filter(is_kid=True)
        self.fields['assigned_to'].queryset = kids
        self.fields['assigned_to'].empty_label = "Select a kid"
        if kids.exists() and not self.is_bound:
            self.fields['assigned_to'].initial = kids.first()

    def clean(self):
        cleaned = super().clean()
        preset_key = cleaned.get('preset')
        preset = TASK_PRESETS.get(preset_key)
        if preset:
            cleaned['title'] = cleaned.get('title') or preset['title']
            cleaned['description'] = cleaned.get('description') or preset['description']
            cleaned['category'] = cleaned.get('category') or preset['category']
            cleaned['points_value'] = cleaned.get('points_value') or preset['points']
        return cleaned


class BehaviorLogForm(forms.ModelForm):
    preset = forms.ChoiceField(
        choices=[('', 'Custom behavior')] + [(key, value[1]) for key, value in BEHAVIOR_PRESETS.items()],
        required=False,
    )

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

    def clean(self):
        cleaned = super().clean()
        preset = BEHAVIOR_PRESETS.get(cleaned.get('preset'))
        if preset:
            cleaned['behavior_type'] = cleaned.get('behavior_type') or preset[0]
            cleaned['description'] = cleaned.get('description') or preset[1]
            cleaned['points_value'] = cleaned.get('points_value') or preset[2]
        return cleaned


class RewardCreateForm(forms.ModelForm):
    preset = forms.ChoiceField(
        choices=[('', 'Custom reward')] + [(key, value[0]) for key, value in REWARD_PRESETS.items()],
        required=False,
    )
    icon = forms.ChoiceField(choices=REWARD_ICONS, widget=forms.RadioSelect)

    class Meta:
        model = Reward
        fields = ['title', 'description', 'points_cost', 'icon', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Extra screen time'}),
            'description': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional details...'}),
            'points_cost': forms.NumberInput(attrs={'min': 1}),
        }

    def clean(self):
        cleaned = super().clean()
        preset = REWARD_PRESETS.get(cleaned.get('preset'))
        if preset:
            cleaned['title'] = cleaned.get('title') or preset[0]
            cleaned['description'] = cleaned.get('description') or preset[1]
            cleaned['points_cost'] = cleaned.get('points_cost') or preset[2]
            cleaned['icon'] = cleaned.get('icon') or preset[3]
        return cleaned


class TaskCompleteForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['fun_rating', 'effort_note', 'did_not_finish', 'not_quite']
        widgets = {
            'fun_rating': forms.RadioSelect,
            'effort_note': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Optional: what helped, what was hard, or what you finished.',
            }),
        }


class TaskReviewForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['points_earned', 'parent_feedback']
        widgets = {
            'points_earned': forms.NumberInput(attrs={'min': -100, 'max': 100}),
            'parent_feedback': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Optional encouragement or reset note for the kid.',
            }),
        }

    def clean_points_earned(self):
        value = self.cleaned_data['points_earned']
        if value is None:
            raise forms.ValidationError('Enter the actual points earned, even if it is 0.')
        return value


class ProfileForm(forms.ModelForm):
    avatar_color = forms.ChoiceField(choices=AVATAR_COLORS, widget=forms.RadioSelect)

    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 'avatar_color',
            'notification_preference', 'preferred_name',
            'age_range', 'motivation_style', 'favorite_rewards',
            'best_task_time', 'reminder_preference', 'overwhelm_triggers',
            'focus_supports', 'sensory_notes', 'goals',
            'household_timezone', 'feedback_preferences', 'default_approval_note',
        ]
        widgets = {
            'favorite_rewards': forms.Textarea(attrs={'rows': 2}),
            'overwhelm_triggers': forms.Textarea(attrs={'rows': 2}),
            'focus_supports': forms.Textarea(attrs={'rows': 2}),
            'sensory_notes': forms.Textarea(attrs={'rows': 2}),
            'goals': forms.Textarea(attrs={'rows': 2}),
            'feedback_preferences': forms.Textarea(attrs={'rows': 2}),
            'default_approval_note': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.is_parent:
            for field in [
                'age_range', 'motivation_style', 'favorite_rewards', 'best_task_time',
                'reminder_preference', 'overwhelm_triggers', 'focus_supports',
                'sensory_notes', 'goals',
            ]:
                self.fields[field].required = False
