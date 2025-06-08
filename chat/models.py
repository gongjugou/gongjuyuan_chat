from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from django.dispatch import receiver
from django.db.models.signals import post_save

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
    """存储所有可用的AI模型信息"""
    name = models.CharField(max_length=100, verbose_name="模型名称")
    model_type = models.CharField(
        max_length=20,
        choices=ModelType.choices,
        verbose_name="模型类型"
    )
    api_url = models.URLField(verbose_name="API地址", blank=True, null=True)
    api_key = models.CharField(max_length=255, verbose_name="API密钥", blank=True, null=True)
    max_tokens_limit = models.IntegerField(
        verbose_name="最大token限制", 
        null=True, 
        blank=True,
        help_text="该模型单次请求允许的最大token数"
    )
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="创建人",
        related_name="chat_aimodels"  # 添加这一行
    )
    description = models.TextField(verbose_name="模型描述", blank=True)
    
    # 定价字段
    input_token_price = models.DecimalField(
        max_digits=12, 
        decimal_places=10,
        default=0,
        verbose_name="输入token单价(每千token)"
    )
    output_token_price = models.DecimalField(
        max_digits=12,
        decimal_places=10,
        default=0,
        verbose_name="输出token单价(每千token)"
    )

    class Meta:
        verbose_name = "AI模型"
        verbose_name_plural = "AI模型"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model_type', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_model_type_display()})"

    def calculate_cost(self, input_tokens, output_tokens):
        """计算使用成本"""
        input_cost = (input_tokens / 1000) * self.input_token_price
        output_cost = (output_tokens / 1000) * self.output_token_price
        return round(input_cost + output_cost, 6)

class Application(models.Model):
    """用户创建的应用"""
    name = models.CharField(max_length=100, verbose_name="应用名称")
    description = models.TextField(verbose_name="应用描述", blank=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='applications',
        verbose_name="创建者",
        null=True,
        blank=True
    )
    model = models.ForeignKey(
        AIModel,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="使用的模型",
        limit_choices_to={'is_active': True}
    )
    # 添加与向量模型的关联
    embedding_model = models.ForeignKey(
        'embeddings.EmbeddingModel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="向量模型",
        help_text="选择用于知识库的向量模型，选择后即可使用知识库功能"
    )
    # 知识库相关设置
    knowledge_similarity_threshold = models.FloatField(
        default=0.5,
        verbose_name="知识相似度阈值",
        help_text="知识匹配的最小相似度阈值(0-1之间)，建议设置为0.5-0.7之间"
    )
    max_knowledge_items = models.IntegerField(
        default=3,
        verbose_name="最大知识条数",
        help_text="每次对话最多使用的知识条数"
    )
    system_role = models.TextField(
        verbose_name="系统角色",
        blank=True,
        default="你是一个智能助手，可以帮助用户解答问题。请保持友好和专业的态度。",
        help_text="设置AI助手的角色和行为"
    )
    show_reasoning = models.BooleanField(
        default=False,
        verbose_name="显示思考过程"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    
    class Meta:
        verbose_name = "应用"
        verbose_name_plural = "应用"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.user.username if self.user else '匿名用户'})"
        
    def clean(self):
        """验证模型设置"""
        from django.core.exceptions import ValidationError
        
        # 验证相似度阈值
        if self.knowledge_similarity_threshold < 0 or self.knowledge_similarity_threshold > 1:
            raise ValidationError({
                'knowledge_similarity_threshold': '相似度阈值必须在0到1之间'
            })
            
        # 验证最大知识条数
        if self.max_knowledge_items < 1:
            raise ValidationError({
                'max_knowledge_items': '最大知识条数必须大于0'
            })

class ChatConversation(models.Model):
    """用户对话会话记录"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='conversations',
        verbose_name="用户",
        null=True,
        blank=True
    )
    session_id = models.CharField(
        max_length=64,
        verbose_name="会话标识符",
        null=True,
        blank=True,
        db_index=True
    )
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='conversations',
        verbose_name="所属应用",
        null=True,
        blank=True
    )
    conversation_id = models.CharField(
        max_length=64, 
        unique=True, 
        db_index=True,
        verbose_name="会话ID"
    )
    title = models.CharField(
        max_length=128, 
        blank=True,
        verbose_name="对话标题"
    )
    model = models.ForeignKey(
        AIModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="主要使用模型"
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    is_active = models.BooleanField(default=True, verbose_name="是否活跃")
    total_tokens = models.PositiveIntegerField(
        default=0,
        verbose_name="总token用量"
    )
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0,
        verbose_name="总成本"
    )
    
    # 对话设置
    temperature = models.FloatField(
        null=True,
        blank=True,
        verbose_name="温度参数"
    )
    top_p = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Top-P参数"
    )
    
    class Meta:
        verbose_name = "聊天会话"
        verbose_name_plural = "聊天会话"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        user_str = f"{self.user.username} - " if self.user else "匿名用户 - "
        return f"{user_str}{self.title or '未命名对话'}"

    def update_stats(self):
        """更新会话的统计信息"""
        aggregates = self.messages.aggregate(
            total_tokens=Sum('tokens'),
            total_cost=Sum('cost')
        )
        self.total_tokens = aggregates['total_tokens'] or 0
        self.total_cost = aggregates['total_cost'] or 0
        self.save()

class ChatMessage(models.Model):
    """单条聊天消息记录"""
    ROLE_CHOICES = [
        ('system', '系统'),
        ('user', '用户'),
        ('assistant', '助手'),
        ('function', '函数'),
    ]
    
    conversation = models.ForeignKey(
        ChatConversation, 
        on_delete=models.CASCADE, 
        related_name='messages',
        verbose_name="所属会话"
    )
    role = models.CharField(
        max_length=9, 
        choices=ROLE_CHOICES,
        verbose_name="角色"
    )
    content = models.TextField(verbose_name="内容")
    reasoning = models.TextField(
        verbose_name="思考过程",
        blank=True,
        null=True,
        help_text="AI助手的思考过程"
    )
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="时间戳")
    tokens = models.PositiveIntegerField(default=0, verbose_name="token数")
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="调用成本"
    )
    
    # API相关字段
    model_used = models.ForeignKey(
        AIModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="使用的模型"
    )
    api_response = models.JSONField(
        null=True, 
        blank=True,
        verbose_name="API响应"
    )
    latency = models.FloatField(
        null=True,
        blank=True,
        verbose_name="响应时间(秒)"
    )
    is_success = models.BooleanField(
        default=True,
        verbose_name="是否成功"
    )
    
    # 调用参数
    temperature = models.FloatField(
        null=True,
        blank=True,
        verbose_name="温度参数"
    )
    top_p = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Top-P参数"
    )
    max_tokens = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="最大token数"
    )
    
    class Meta:
        verbose_name = "聊天消息"
        verbose_name_plural = "聊天消息"
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['conversation', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.conversation.id} - {self.get_role_display()}: {self.content[:50]}"

class ModelUsageStat(models.Model):
    """模型使用统计(按日)"""
    model = models.ForeignKey(
        AIModel,
        on_delete=models.CASCADE,
        related_name='usage_stats',
        verbose_name="模型"
    )
    date = models.DateField(verbose_name="统计日期")
    call_count = models.PositiveIntegerField(
        default=0,
        verbose_name="调用次数"
    )
    total_tokens = models.PositiveIntegerField(
        default=0,
        verbose_name="总token数"
    )
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0,
        verbose_name="总成本"
    )
    
    class Meta:
        verbose_name = "模型使用统计"
        verbose_name_plural = "模型使用统计"
        unique_together = ('model', 'date')
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.model.name} - {self.date}: {self.call_count}次调用"

# 信号处理
@receiver(post_save, sender=ChatMessage)
def update_conversation_stats(sender, instance, **kwargs):
    """当消息保存时自动更新会话统计"""
    instance.conversation.update_stats()

@receiver(post_save, sender=ChatMessage)
def update_model_stats(sender, instance, **kwargs):
    """当消息保存时更新模型使用统计"""
    if instance.model_used and instance.is_success:
        date = instance.timestamp.date()
        stat, created = ModelUsageStat.objects.get_or_create(
            model=instance.model_used,
            date=date,
            defaults={
                'call_count': 0,
                'total_tokens': 0,
                'total_cost': 0
            }
        )
        stat.call_count += 1
        stat.total_tokens += instance.tokens
        stat.total_cost += instance.cost if instance.cost else 0
        stat.save()