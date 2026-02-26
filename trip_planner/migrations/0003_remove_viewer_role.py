# Migration to remove VIEWER role: convert existing VIEWER to FLEET_MANAGER, then update choices

from django.db import migrations, models


def convert_viewer_to_fleet_manager(apps, schema_editor):
    OrganizationMember = apps.get_model("trip_planner", "OrganizationMember")
    Invitation = apps.get_model("trip_planner", "Invitation")
    OrganizationMember.objects.filter(role="VIEWER").update(role="FLEET_MANAGER")
    Invitation.objects.filter(role="VIEWER").update(role="FLEET_MANAGER")


def reverse_convert(apps, schema_editor):
    # No reverse - we cannot reliably restore VIEWER
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("trip_planner", "0002_alter_auditlog_action_alter_dutystatussegment_status_and_more"),
    ]

    operations = [
        migrations.RunPython(convert_viewer_to_fleet_manager, reverse_convert),
        migrations.AlterField(
            model_name="invitation",
            name="role",
            field=models.CharField(
                choices=[
                    ("PLATFORM_ADMIN", "Platform Admin"),
                    ("ORG_ADMIN", "Org Admin"),
                    ("DISPATCHER", "Dispatcher"),
                    ("DRIVER", "Driver"),
                    ("FLEET_MANAGER", "Fleet Manager"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="organizationmember",
            name="role",
            field=models.CharField(
                choices=[
                    ("PLATFORM_ADMIN", "Platform Admin"),
                    ("ORG_ADMIN", "Org Admin"),
                    ("DISPATCHER", "Dispatcher"),
                    ("DRIVER", "Driver"),
                    ("FLEET_MANAGER", "Fleet Manager"),
                ],
                max_length=20,
            ),
        ),
    ]
