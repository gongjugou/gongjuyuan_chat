from django.db import models
from django.contrib.auth.models import User

class ModelType(models.TextChoices):
    LLM = 'LLM', '大语言模型'
    EMBEDDING = 'EMBEDDING', '向量模型'
    ASR = 'ASR', '语音识别'
    TTS = 'TTS', '语音合成'
    RERANK = 'RERANK', '重排模型'
    VISION = 'VISION', '视觉模型'
    IMAGE_GEN = 'IMAGE_GEN', '图片生成'
    BASE = 'BASE', '基础模型'

class AIModel(models.Model):
    name = models.CharField(max_length=100, verbose_name="模型名称")
    model_type = models.CharField(
        max_length=20,
        choices=ModelType.choices,
        verbose_name="模型类型"
    )
    api_url = models.URLField(verbose_name="API地址", blank=True, null=True)
    api_key = models.CharField(max_length=255, verbose_name="API密钥", blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="创建人"
    )
    description = models.TextField(verbose_name="模型描述", blank=True)
    max_tokens_limit = models.IntegerField(
        verbose_name="最大token限制", 
        null=True, 
        blank=True,
        help_text="该模型单次请求允许的最大token数"
    )

    class Meta:
        verbose_name = "AI模型"
        verbose_name_plural = "AI模型"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_model_type_display()})"