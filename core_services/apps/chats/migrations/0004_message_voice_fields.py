import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chats", "0003_chatuserpresence"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="audio_file",
            field=models.FileField(blank=True, null=True, upload_to="chat/audio/%Y/%m/%d/"),
        ),
        migrations.AddField(
            model_name="message",
            name="duration_ms",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="message",
            name="message_type",
            field=models.CharField(choices=[("TEXT", "Text"), ("VOICE", "Voice"), ("SYSTEM", "System")], default="TEXT", max_length=20),
        ),
    ]
