# Generated by Django 4.2.5 on 2025-06-06 14:31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AIModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='模型名称')),
                ('model_type', models.CharField(choices=[('LLM', '大语言模型'), ('EMBEDDING', '向量模型'), ('ASR', '语音识别'), ('TTS', '语音合成'), ('RERANK', '重排模型'), ('VISION', '视觉模型'), ('IMAGE_GEN', '图片生成'), ('BASE', '基础模型')], max_length=20, verbose_name='模型类型')),
                ('api_url', models.URLField(blank=True, null=True, verbose_name='API地址')),
                ('api_key', models.CharField(blank=True, max_length=255, null=True, verbose_name='API密钥')),
                ('max_tokens_limit', models.IntegerField(blank=True, help_text='该模型单次请求允许的最大token数', null=True, verbose_name='最大token限制')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否激活')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('description', models.TextField(blank=True, verbose_name='模型描述')),
                ('input_token_price', models.DecimalField(decimal_places=10, default=0, max_digits=12, verbose_name='输入token单价(每千token)')),
                ('output_token_price', models.DecimalField(decimal_places=10, default=0, max_digits=12, verbose_name='输出token单价(每千token)')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='chat_aimodels', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
            ],
            options={
                'verbose_name': 'AI模型',
                'verbose_name_plural': 'AI模型',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ChatConversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('conversation_id', models.CharField(db_index=True, max_length=64, unique=True, verbose_name='会话ID')),
                ('title', models.CharField(blank=True, max_length=128, verbose_name='对话标题')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否活跃')),
                ('total_tokens', models.PositiveIntegerField(default=0, verbose_name='总token用量')),
                ('total_cost', models.DecimalField(decimal_places=6, default=0, max_digits=10, verbose_name='总成本')),
                ('temperature', models.FloatField(blank=True, null=True, verbose_name='温度参数')),
                ('top_p', models.FloatField(blank=True, null=True, verbose_name='Top-P参数')),
                ('model', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='chat.aimodel', verbose_name='主要使用模型')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversations', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '聊天会话',
                'verbose_name_plural': '聊天会话',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='ModelUsageStat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='统计日期')),
                ('call_count', models.PositiveIntegerField(default=0, verbose_name='调用次数')),
                ('total_tokens', models.PositiveIntegerField(default=0, verbose_name='总token数')),
                ('total_cost', models.DecimalField(decimal_places=6, default=0, max_digits=10, verbose_name='总成本')),
                ('model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usage_stats', to='chat.aimodel', verbose_name='模型')),
            ],
            options={
                'verbose_name': '模型使用统计',
                'verbose_name_plural': '模型使用统计',
                'ordering': ['-date'],
                'unique_together': {('model', 'date')},
            },
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('system', '系统'), ('user', '用户'), ('assistant', '助手'), ('function', '函数')], max_length=9, verbose_name='角色')),
                ('content', models.TextField(verbose_name='内容')),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now, verbose_name='时间戳')),
                ('tokens', models.PositiveIntegerField(default=0, verbose_name='token数')),
                ('cost', models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True, verbose_name='调用成本')),
                ('api_response', models.JSONField(blank=True, null=True, verbose_name='API响应')),
                ('latency', models.FloatField(blank=True, null=True, verbose_name='响应时间(秒)')),
                ('is_success', models.BooleanField(default=True, verbose_name='是否成功')),
                ('temperature', models.FloatField(blank=True, null=True, verbose_name='温度参数')),
                ('top_p', models.FloatField(blank=True, null=True, verbose_name='Top-P参数')),
                ('max_tokens', models.IntegerField(blank=True, null=True, verbose_name='最大token数')),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='chat.chatconversation', verbose_name='所属会话')),
                ('model_used', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='chat.aimodel', verbose_name='使用的模型')),
            ],
            options={
                'verbose_name': '聊天消息',
                'verbose_name_plural': '聊天消息',
                'ordering': ['timestamp'],
                'indexes': [models.Index(fields=['conversation', 'timestamp'], name='chat_chatme_convers_af799d_idx')],
            },
        ),
        migrations.AddIndex(
            model_name='chatconversation',
            index=models.Index(fields=['user', 'is_active'], name='chat_chatco_user_id_c00d1e_idx'),
        ),
        migrations.AddIndex(
            model_name='aimodel',
            index=models.Index(fields=['model_type', 'is_active'], name='chat_aimode_model_t_1603ad_idx'),
        ),
    ]
