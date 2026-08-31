"""Admin forms.

Django's `UserCreationForm` and `UserChangeForm` name `username` in their
`Meta.fields` outright, so with email as `USERNAME_FIELD` the add form would
still demand a username and the admin could not create an account without
one. These subclasses swap that field for the email address, and replace the
form field Django pairs with a username -- see below for why it cannot cope
with an optional one.
"""

from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm, UsernameField

from .models import CustomUser


class OptionalUsernameField(UsernameField):
    """`UsernameField` that tolerates the field being left empty.

    Django's assumes a username is always given: it normalizes the value with
    `len(value)` in hand, and the empty value of a form field derived from a
    nullable CharField is None rather than ''. Submitting the admin's add form
    without a username raises `TypeError` inside Django itself.
    """

    def to_python(self, value):
        value = forms.CharField.to_python(self, value)
        if value in self.empty_values:
            # None, not '': the column is unique, so blank has to stay NULL.
            return None
        return super().to_python(value)


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('email',)
        field_classes = {'username': OptionalUsernameField}


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = '__all__'
        field_classes = {'username': OptionalUsernameField}
