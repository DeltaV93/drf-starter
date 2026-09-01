from collections.abc import Mapping

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.users.serializers import UserSerializer

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True, required=True, style={'input_type': 'password'}
    )

    # Declared rather than inferred from the model, to drop the unique
    # validator ModelSerializer would attach: `validate_username` below owns
    # uniqueness, and it compares case-insensitively. The account is
    # identified by its email -- a username is a display handle people may
    # want and may equally skip, so missing, empty and null all mean "none".
    username = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=150,
        validators=[UnicodeUsernameValidator()],
        help_text='Optional. Sign-in uses the email address.',
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password', 'password2')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
        }

    def validate_email(self, value):
        # Addresses are stored lowercased, but rows predating that are not,
        # so the uniqueness check cannot assume it.
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with that email already exists.')
        # Normalized here as well as in CustomUser.save(), so what the
        # response echoes back is what was stored.
        return User.objects.normalize_email(value)

    def validate_username(self, value):
        if not value:
            # Normalized to None rather than '', because the column is unique
            # and only one row may hold any given non-null value.
            return None

        if '@' in value:
            # Sign-in resolves an identifier against emails before usernames,
            # so a username shaped like an address is one nobody could ever
            # sign in with -- and might belong to somebody else.
            raise serializers.ValidationError(
                'A username cannot contain "@". Sign in with your email address instead.'
            )

        # Uniqueness is enforced case-insensitively for the same reason the
        # sign-in lookup is: `Ada` and `ada` must not be two accounts.
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('A user with that username already exists.')

        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password2': "Password fields didn't match."})

        # Run Django's validators here rather than as a field-level validator so
        # they can compare the password against the username and email.
        user = User(
            username=attrs.get('username'),
            email=attrs.get('email'),
            first_name=attrs.get('first_name', ''),
            last_name=attrs.get('last_name', ''),
        )
        try:
            validate_password(attrs['password'], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': list(exc.messages)}) from exc

        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class AuthenticatedSerializer(serializers.Serializer):
    """What a successful sign-in hands back.

    `user` and `csrfToken` are absent when `twoFactorRequired` is true: the
    password was right but the session is not authenticated yet, so there is
    no user to describe. Clients must branch on that flag rather than reading
    `user` unconditionally.
    """

    user = UserSerializer(read_only=True, required=False)
    csrfToken = serializers.CharField(read_only=True, required=False)
    twoFactorRequired = serializers.BooleanField(read_only=True, required=False)
    method = serializers.CharField(
        read_only=True,
        required=False,
        help_text='Which second factor was accepted: "totp" or "recovery_code".',
    )


class UserLoginSerializer(serializers.Serializer):
    """Credentials for both the session and the token sign-in.

    One identifier field, not two: usernames are optional, so what a client
    holds may be either an email address or a handle, and asking it to know
    which only moves the branch into the client.
    """

    identifier = serializers.CharField(
        max_length=255,
        help_text='Email address, or username for an account that has one.',
    )
    password = serializers.CharField(
        max_length=128, write_only=True, style={'input_type': 'password'}
    )

    # What clients built against the pre-`identifier` API post. Accepted so a
    # mobile build already in the app stores keeps signing people in; new
    # clients should send `identifier`.
    LEGACY_IDENTIFIER_FIELDS = ('username', 'email')

    @classmethod
    def read_identifier(cls, data):
        """The identifier a request offers, under whichever name.

        Views use this for the audit trail, which has to record the account
        that was tried even when validation rejected the request -- including
        when what arrived was not an object at all.
        """
        if not isinstance(data, Mapping):
            return ''

        for field in ('identifier', *cls.LEGACY_IDENTIFIER_FIELDS):
            value = data.get(field)
            if value and isinstance(value, str):
                return value
        return ''

    def to_internal_value(self, data):
        # A body that is not an object at all is DRF's to reject, with the 400
        # it has always answered -- reading `identifier` off a list first would
        # make it a 500.
        if not isinstance(data, Mapping):
            return super().to_internal_value(data)

        if not data.get('identifier'):
            legacy = self.read_identifier(data)
            if legacy:
                # .copy() rather than {**data}: a QueryDict is a dict subclass
                # whose values are internally lists, so unpacking one hands
                # every field to the serializer wrapped in a list.
                data = data.copy()
                data['identifier'] = legacy
        return super().to_internal_value(data)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get('request'),
            username=attrs['identifier'],
            password=attrs['password'],
        )
        if not user:
            # Deliberately identical for "no such user", "wrong password" and
            # "inactive account" so the endpoint cannot enumerate accounts.
            raise serializers.ValidationError(
                'Unable to log in with provided credentials.', code='authorization'
            )

        attrs['user'] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})

        try:
            validate_password(attrs['password'])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': list(exc.messages)}) from exc

        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


class AccountDeletionSerializer(serializers.Serializer):
    """Confirms the caller's password before anonymizing their account."""

    password = serializers.CharField(
        write_only=True, required=True, style={'input_type': 'password'}
    )
    reason = serializers.CharField(max_length=1000, required=False, allow_blank=True)

    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Incorrect password.')
        return value
