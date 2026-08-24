from django import forms
from django.forms import modelformset_factory, BaseModelFormSet
from .models import Course, PaymentMethod, LiveSession, Coupon

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'price', 'duration', 'mode', 'total_hours', 'curriculum']
        widgets = {
            'curriculum': forms.Textarea(attrs={'rows': 5}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class PaymentMethodForm(forms.ModelForm):
    """Custom form for PaymentMethod that doesn't require the id field"""
    class Meta:
        model = PaymentMethod
        fields = ['method_type', 'merchant_id', 'merchant_name']
        widgets = {
            'merchant_id': forms.TextInput(attrs={'placeholder': 'e.g., 123456'}),
            'merchant_name': forms.TextInput(attrs={'placeholder': 'e.g., Radoki Solutions'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields not required to allow empty forms
        for field in self.fields.values():
            field.required = False
    
    def clean(self):
        """Custom clean method to skip id validation"""
        cleaned_data = super().clean()
        # Don't require any field for empty forms
        if not any([cleaned_data.get('method_type'), cleaned_data.get('merchant_id'), cleaned_data.get('merchant_name')]):
            # All fields are empty, so clear any errors
            self.cleaned_data = cleaned_data
            return cleaned_data
        return cleaned_data

class BasePaymentMethodFormSet(BaseModelFormSet):
    """Custom formset to handle empty forms without validation errors"""
    def clean(self):
        """Skip parent validation to avoid id field requirement"""
        # Don't call parent's clean() - we handle validation at form level
        pass

PaymentMethodFormSet = modelformset_factory(
    PaymentMethod,
    form=PaymentMethodForm,
    extra=1,
    can_delete=True,
    formset=BasePaymentMethodFormSet,
)

from .models import Resource, LessonRecording, LessonRecordingResource, LessonVideoLink, LessonAdditionalResource

class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ['title', 'file', 'download_allowed']
        widgets = {
            'download_allowed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LessonVideoLinkForm(forms.ModelForm):
    class Meta:
        model = LessonVideoLink
        fields = ['title', 'youtube_url']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Video title'}),
            'youtube_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://youtube.com/watch?v=...'}),
        }

    def clean_youtube_url(self):
        value = self.cleaned_data['youtube_url']
        if 'youtube.com/' not in value and 'youtu.be/' not in value:
            raise forms.ValidationError('Enter a valid YouTube link.')
        return value


class LessonAdditionalResourceForm(forms.ModelForm):
    class Meta:
        model = LessonAdditionalResource
        fields = ['title', 'file']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Resource title'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_file(self):
        resource_file = self.cleaned_data['file']
        if resource_file.size > 50 * 1024 * 1024:
            raise forms.ValidationError('Lesson resources must be 50 MB or smaller.')
        return resource_file


class LessonRecordingForm(forms.ModelForm):
    """Form used by instructors to add a video recording to a lesson."""
    class Meta:
        model = LessonRecording
        fields = ['title', 'video', 'youtube_url', 'resource_file', 'duration_minutes', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Week 1 recorded session',
            }),
            'video': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'video/mp4,video/webm,video/quicktime,video/x-m4v',
            }),
            'youtube_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional YouTube recording link',
            }),
            'resource_file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
            }),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_video(self):
        video = self.cleaned_data['video']
        if not video:
            return video
        max_size = 1024 * 1024 * 1024
        if video.size > max_size:
            raise forms.ValidationError('Video files must be 1 GB or smaller.')
        return video

    def clean_resource_file(self):
        resource_file = self.cleaned_data['resource_file']
        if resource_file and resource_file.size > 50 * 1024 * 1024:
            raise forms.ValidationError('Session resources must be 50 MB or smaller.')
        return resource_file

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('video') and not cleaned_data.get('youtube_url'):
            raise forms.ValidationError('Add an uploaded video or a YouTube recording link.')
        return cleaned_data


class LessonRecordingResourceForm(forms.ModelForm):
    class Meta:
        model = LessonRecordingResource
        fields = ['title', 'file']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Session notes',
            }),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_file(self):
        resource_file = self.cleaned_data['file']
        if resource_file.size > 50 * 1024 * 1024:
            raise forms.ValidationError('Session resources must be 50 MB or smaller.')
        return resource_file


class LiveSessionForm(forms.ModelForm):
    """Form for instructors to create and edit live sessions."""
    scheduled_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control',
        }),
        help_text='Date and time when the session will be held'
    )

    class Meta:
        model = LiveSession
        fields = ['title', 'description', 'meeting_link', 'scheduled_at']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "e.g., 'Week 1 Introduction'",
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Session details and agenda',
            }),
            'meeting_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://zoom.us/j/... or https://meet.google.com/...',
            }),
        }


class CouponForm(forms.ModelForm):
    """Form for instructors/admins to create and manage coupon codes."""
    valid_from = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control',
        }),
        required=False,
        help_text='When the coupon becomes valid (leave blank for immediate)'
    )
    valid_until = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control',
        }),
        required=False,
        help_text='When the coupon expires (leave blank for no expiration)'
    )
    
    class Meta:
        model = Coupon
        fields = ['code', 'description', 'discount_type', 'discount_value', 'courses', 'valid_from', 'valid_until', 'max_uses', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., SAVE20, SPRING2024',
                'style': 'text-transform: uppercase;',
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Spring Sale - 20% Off',
            }),
            'discount_type': forms.Select(attrs={
                'class': 'form-control',
            }),
            'discount_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter percentage (0-100) or fixed amount',
                'step': '0.01',
            }),
            'courses': forms.SelectMultiple(attrs={
                'class': 'form-select form-select-lg',
                'size': '8',
            }),
            'max_uses': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Leave blank for unlimited uses',
                'min': '1',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


