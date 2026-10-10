from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
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

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password', 'password2')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
        }

    def validate_email(self, value):
        email = User.objects.normalize_email(value)
        # Checked here rather than left to the database constraint so the
        # answer arrives as a field error instead of an IntegrityError.
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('A user with that email already exists.')
        return email

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password2': "Password fields didn't match."})

        # Run Django's validators here rather than as a field-level validator so
        # they can compare the password against the email address and name.
        user = User(
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
        return User.objects.create_user(password=password, **validated_data)


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
    email = serializers.EmailField()
    password = serializers.CharField(
        max_length=128, write_only=True, style={'input_type': 'password'}
    )

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get('request'),
            email=attrs['email'],
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
