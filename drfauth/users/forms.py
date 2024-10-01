import re

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import Profile, Comment, checkmk
from django.core.exceptions import ValidationError


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_image']


class checkimage(forms.ModelForm):
    class Meta:
        model = checkmk
        fields = ['d_image']


class CommentForm(forms.ModelForm):
    content = forms.CharField(label="", widget=forms.Textarea(
        attrs={
            'class': 'form-control',
            'placeholder': 'Comment here!',
            'rows': 4,
            'cols': 50
        }))

    class Meta:
        model = Comment
        fields = ['content']

def password_validator(password):
    if re.match('^(?=.*[a-z])(?=.*[A-Z])(?=.*[@$!%*#?&])(?=.*[0-9])[A-Za-z\d@$!#%*?&]{8,16}$', password):
        return True
    return False

class CustomPasswordChangeForm(PasswordChangeForm):
    error_messages = {'password_incorrect': 'The current password you entered is incorrect. Please try again',
                      'password_mismatch': 'New password & re-enter password must be the same.'}

    def __init__(self, *args, **kwargs):
        super(CustomPasswordChangeForm, self).__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update(
            {'class': 'form-control', 'placeholder': 'Enter Current Password'})
        self.fields['new_password1'].widget.attrs.update(
            {'class': 'form-control', 'placeholder': 'Enter New Password.'})
        self.fields['new_password2'].widget.attrs.update(
            {'class': 'form-control', 'placeholder': 'Confirm New Password'})
        self.fields['old_password'].label = "Current Password"
        self.fields['new_password1'].label = "New Password"
        self.fields['new_password2'].label = "Confirm New Password"

    def clean_new_password1(self):
        new_password1 = self.cleaned_data['new_password1']
        if not password_validator(new_password1):
            raise ValidationError(
                "Your new password must be at least 8 characters long and contain"
                " at least one uppercase letter, one lowercase letter, one number, and one special character.")
        return new_password1

    def clean_new_password2(self):
        new_password2 = self.cleaned_data['new_password2']
        if not password_validator(new_password2):
            raise ValidationError(
                "Your new password confirmation must be at least 8 characters long and contain"
                " at least one uppercase letter, one lowercase letter, one number, and one special character.")
        return new_password2

    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get('old_password')
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        if old_password and new_password1:
            if old_password == new_password1:
                raise ValidationError({'new_password1': "New password must not be the same as the current "
                                                        "password."})
            if new_password1 and new_password2:
                if new_password1 != new_password2:
                    raise ValidationError(
                        {'new_password2': "New password & new password confirmation must be the same."})
        return cleaned_data

