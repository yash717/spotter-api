from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from trip_planner.constants import MemberRole
from trip_planner.models import Organization, OrganizationMember


class OrganizationSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "dot_number",
            "mc_number",
            "primary_contact_email",
            "address",
            "phone",
            "logo_url",
            "invitation_expiry_days",
            "is_active",
            "created_at",
            "updated_at",
            "member_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "member_count"]

    @extend_schema_field(serializers.IntegerField())
    def get_member_count(self, obj):
        return obj.members.filter(is_active=True).count()


class MemberSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    full_name = serializers.SerializerMethodField()
    deactivated_by_email = serializers.SerializerMethodField()
    invited_by_email = serializers.SerializerMethodField()
    email_verified = serializers.BooleanField(source="user.email_verified", read_only=True)

    class Meta:
        model = OrganizationMember
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "is_active",
            "email_verified",
            "joined_at",
            "deactivated_at",
            "deactivated_by_email",
            "invited_by_email",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email

    @extend_schema_field(serializers.EmailField(allow_null=True))
    def get_deactivated_by_email(self, obj):
        return obj.deactivated_by.email if obj.deactivated_by else None

    @extend_schema_field(serializers.EmailField(allow_null=True))
    def get_invited_by_email(self, obj):
        return obj.invited_by.email if obj.invited_by else None


class MemberUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=[
            (MemberRole.ORG_ADMIN, "Org Admin"),
            (MemberRole.DISPATCHER, "Dispatcher"),
            (MemberRole.DRIVER, "Driver"),
            (MemberRole.FLEET_MANAGER, "Fleet Manager"),
        ]
    )
