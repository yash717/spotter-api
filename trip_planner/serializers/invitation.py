from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from trip_planner.constants import InvitationStatus, MemberRole
from trip_planner.models import Invitation, OrganizationMember


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=MemberRole.INVITABLE_CHOICES)
    personal_message = serializers.CharField(max_length=500, required=False, default="")

    def validate_email(self, value):
        return value.lower()

    def validate(self, attrs):
        org = self.context.get("organization")
        email = attrs["email"]
        if OrganizationMember.objects.filter(
            organization=org, user__email=email, is_active=True
        ).exists():
            raise serializers.ValidationError(
                {"email": "This email is already an active member of your organization."}
            )
        pending = Invitation.objects.filter(
            organization=org, email=email, status=InvitationStatus.PENDING
        ).first()
        if pending:
            raise serializers.ValidationError(
                {
                    "email": "A pending invitation already exists for this email. Revoke it first or resend."
                }
            )
        return attrs


class InvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()
    full_name = serializers.CharField(max_length=255)
    password = serializers.CharField(write_only=True, min_length=8)
    license_number = serializers.CharField(max_length=50, required=False, default="")
    license_state = serializers.CharField(max_length=5, required=False, default="")
    home_terminal_address = serializers.CharField(max_length=500, required=False, default="")
    cycle_used_hours = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        required=False,
        default=0,
        min_value=0,
        max_value=70,
    )
    truck_number = serializers.CharField(max_length=50, required=False, default="")
    trailer_number = serializers.CharField(max_length=50, required=False, default="")
    license_plate = serializers.CharField(max_length=20, required=False, default="")
    odometer = serializers.DecimalField(max_digits=10, decimal_places=1, required=False, default=0)


class InvitationListSerializer(serializers.ModelSerializer):
    invited_by_email = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = [
            "id",
            "email",
            "role",
            "status",
            "expires_at",
            "sent_at",
            "accepted_at",
            "personal_message",
            "resend_count",
            "last_resent_at",
            "invited_by_email",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.EmailField(allow_null=True))
    def get_invited_by_email(self, obj):
        return obj.invited_by.email if obj.invited_by else None


class InvitationDetailSerializer(serializers.ModelSerializer):
    invited_by_email = serializers.SerializerMethodField()
    accepted_by_email = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = [
            "id",
            "email",
            "role",
            "status",
            "expires_at",
            "sent_at",
            "accepted_at",
            "personal_message",
            "resend_count",
            "last_resent_at",
            "invited_by_email",
            "accepted_by_email",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.EmailField(allow_null=True))
    def get_invited_by_email(self, obj):
        return obj.invited_by.email if obj.invited_by else None

    @extend_schema_field(serializers.EmailField(allow_null=True))
    def get_accepted_by_email(self, obj):
        return obj.accepted_by.email if obj.accepted_by else None
