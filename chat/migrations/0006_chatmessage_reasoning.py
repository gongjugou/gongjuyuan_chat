# Generated by Django 4.2.5 on 2025-06-07 14:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0005_chatconversation_session_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='reasoning',
            field=models.TextField(blank=True, help_text='AI助手的思考过程', null=True, verbose_name='思考过程'),
        ),
    ]
