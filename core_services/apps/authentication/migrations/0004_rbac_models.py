from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("company", "0001_initial"),
        ("authentication", "0003_user_mobile_number_and_must_change_password"),
    ]

    operations = [
        migrations.CreateModel(
            name="Permission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(db_index=True, max_length=120, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["code"],
            },
        ),
        migrations.CreateModel(
            name="Role",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.CharField(db_index=True, max_length=120)),
                ("name", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True, default="")),
                ("is_system", models.BooleanField(db_index=True, default=False)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="company.company")),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="UserRole",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="company.company")),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="role_users", to="authentication.role")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_roles", to="authentication.user")),
            ],
        ),
        migrations.CreateModel(
            name="RolePermission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("permission", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="permission_roles", to="authentication.permission")),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="role_permissions", to="authentication.role")),
            ],
        ),
        migrations.AddField(
            model_name="role",
            name="permissions",
            field=models.ManyToManyField(related_name="roles", through="authentication.RolePermission", to="authentication.permission"),
        ),
        migrations.AddConstraint(
            model_name="role",
            constraint=models.UniqueConstraint(fields=("company", "code"), name="uq_role_company_code"),
        ),
        migrations.AddConstraint(
            model_name="role",
            constraint=models.UniqueConstraint(condition=models.Q(company__isnull=True), fields=("code",), name="uq_role_global_code"),
        ),
        migrations.AddIndex(
            model_name="role",
            index=models.Index(fields=["company", "is_active"], name="authenticati_company_1468d5_idx"),
        ),
        migrations.AddIndex(
            model_name="role",
            index=models.Index(fields=["company", "name"], name="authenticati_company_8cca37_idx"),
        ),
        migrations.AddConstraint(
            model_name="userrole",
            constraint=models.UniqueConstraint(fields=("user", "role", "company"), name="uq_user_role_company"),
        ),
        migrations.AddIndex(
            model_name="userrole",
            index=models.Index(fields=["user", "company", "is_active"], name="authenticati_user_id_761815_idx"),
        ),
        migrations.AddConstraint(
            model_name="rolepermission",
            constraint=models.UniqueConstraint(fields=("role", "permission"), name="uq_role_permission"),
        ),
        migrations.AddIndex(
            model_name="rolepermission",
            index=models.Index(fields=["role", "permission"], name="authenticati_role_id_71d34f_idx"),
        ),
    ]
