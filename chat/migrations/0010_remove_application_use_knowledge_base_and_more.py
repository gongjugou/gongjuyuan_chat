# Generated by Django 4.2.5 on 2025-06-08 06:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('embeddings', '0002_delete_modelparameter'),
        ('chat', '0009_alter_application_embedding_model'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='application',
            name='use_knowledge_base',
        ),
        migrations.AlterField(
            model_name='application',
            name='embedding_model',
            field=models.ForeignKey(blank=True, help_text='选择用于知识库的向量模型，选择后即可使用知识库功能', null=True, on_delete=django.db.models.deletion.SET_NULL, to='embeddings.embeddingmodel', verbose_name='向量模型'),
        ),
    ]
