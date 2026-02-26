from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from trip_planner.constants import MemberRole
from trip_planner.models import Organization, OrganizationMember, User


class RegisterSerializer(serializers.Serializer):
    """Creates an Organization and its first org_admin user."""

    company_name = serializers.CharField(max_length=255)
    dot_number = serializers.CharField(max_length=20, required=False, default="")
    mc_number = serializers.CharField(max_length=20, required=False, default="")
    admin_full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_password(self, value):
        validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["admin_full_name"].split(" ")[0],
            last_name=" ".join(validated_data["admin_full_name"].split(" ")[1:]),
        )
        org = Organization.objects.create(
            name=validated_data["company_name"],
            dot_number=validated_data.get("dot_number", ""),
            mc_number=validated_data.get("mc_number", ""),
            primary_contact_email=validated_data["email"],
        )
        OrganizationMember.objects.create(
            organization=org,
            user=user,
            role=MemberRole.ORG_ADMIN,
        )
        return {"user": user, "organization": org}


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email", "").lower()
        password = attrs.get("password")
        user = authenticate(username=email, password=password)
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("Account is deactivated.")
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "date_joined", "last_login"]
        read_only_fields = fields
