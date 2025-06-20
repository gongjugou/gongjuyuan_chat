# Generated by Django 4.2.5 on 2025-06-08 07:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('embeddings', '0002_delete_modelparameter'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='knowledge',
            name='similarity_score',
        ),
        migrations.AlterField(
            model_name='apicalllog',
            name='api_type',
            field=models.CharField(choices=[('EMBEDDING', '向量生成'), ('CHAT', '对话生成')], max_length=20, verbose_name='API类型'),
        ),
        migrations.AlterField(
            model_name='apicalllog',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='创建时间'),
        ),
        migrations.AlterField(
            model_name='embeddingmodel',
            name='api_key',
            field=models.CharField(max_length=100, verbose_name='API密钥'),
        ),
        migrations.AlterField(
            model_name='embeddingmodel',
            name='encoding_format',
            field=models.CharField(default='float', max_length=20, verbose_name='编码格式'),
        ),
        migrations.AddIndex(
            model_name='apicalllog',
            index=models.Index(fields=['model', 'api_type', 'created_at'], name='embeddings__model_i_f5c5a0_idx'),
        ),
        migrations.AddIndex(
            model_name='knowledge',
            index=models.Index(fields=['model', 'is_valid'], name='embeddings__model_i_7ae304_idx'),
        ),
    ]
