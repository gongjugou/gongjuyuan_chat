from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import Count, Sum
from django.utils.html import format_html
from .models import AIModel, ChatConversation, ChatMessage, ModelUsageStat

# 自定义过滤器
class ActiveModelFilter(admin.SimpleListFilter):
    title = '激活状态'
    parameter_name = 'is_active'

    def lookups(self, request, model_admin):
        return (
            ('yes', '已激活'),
            ('no', '未激活'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(is_active=True)
        if self.value() == 'no':
            return queryset.filter(is_active=False)

# 内联管理类
class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('timestamp', 'role', 'content_preview', 'tokens', 'cost')
    fields = ('timestamp', 'role', 'content_preview', 'model_used', 'tokens', 'cost')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '内容预览'

    def has_add_permission(self, request, obj=None):
        return False

class ModelUsageStatInline(admin.TabularInline):
    model = ModelUsageStat
    extra = 0
    readonly_fields = ('date', 'call_count', 'total_tokens', 'total_cost')
    
    def has_add_permission(self, request, obj=None):
        return False

# 主管理类
@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'model_type_display', 'api_url_short', 'is_active', 'created_at', 'usage_stats')
    list_filter = (ActiveModelFilter, 'model_type', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'total_usage')
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'model_type', 'description', 'is_active')
        }),
        ('API 配置', {
            'fields': ('api_url', 'api_key', 'max_tokens_limit'),
            'classes': ('collapse',)
        }),
        ('定价策略', {
            'fields': ('input_token_price', 'output_token_price'),
            'classes': ('collapse',)
        }),
        ('元信息', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [ModelUsageStatInline]
    
    def model_type_display(self, obj):
        return obj.get_model_type_display()
    model_type_display.short_description = '模型类型'
    
    def api_url_short(self, obj):
        return obj.api_url[:30] + '...' if obj.api_url and len(obj.api_url) > 30 else obj.api_url
    api_url_short.short_description = 'API地址'
    
    def usage_stats(self, obj):
        stats = obj.usage_stats.aggregate(
            total_calls=Sum('call_count'),
            total_tokens=Sum('total_tokens')
        )
        return f"{stats['total_calls'] or 0}次调用, {stats['total_tokens'] or 0} tokens"
    usage_stats.short_description = '使用统计'
    
    def total_usage(self, obj):
        return self.usage_stats(obj)
    total_usage.short_description = '总使用量'
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # 新建时自动设置创建人
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'model', 'message_count', 'total_tokens', 'updated_at')
    list_filter = ('user', 'model', 'is_active', 'updated_at')
    search_fields = ('user__username', 'title', 'conversation_id')
    readonly_fields = ('conversation_id', 'created_at', 'updated_at', 'cost_per_token')
    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'conversation_id', 'title', 'is_active')
        }),
        ('模型设置', {
            'fields': ('model', 'temperature', 'top_p'),
            'classes': ('collapse',)
        }),
        ('统计信息', {
            'fields': ('total_tokens', 'total_cost', 'cost_per_token'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [ChatMessageInline]
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = '消息数'
    
    def cost_per_token(self, obj):
        if obj.total_tokens > 0:
            return f"${(obj.total_cost / obj.total_tokens):.8f}/token"
        return 'N/A'
    cost_per_token.short_description = '单token成本'
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            message_count=Count('messages')
        )

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'role', 'content_preview', 'model_used', 'tokens', 'cost', 'timestamp')
    list_filter = ('role', 'model_used', 'is_success', 'timestamp')
    search_fields = ('content', 'conversation__title')
    readonly_fields = ('timestamp', 'cost_per_token', 'latency_display')
    fieldsets = (
        ('基本信息', {
            'fields': ('conversation', 'role', 'content')
        }),
        ('模型交互', {
            'fields': ('model_used', 'is_success', 'api_response_preview'),
            'classes': ('collapse',)
        }),
        ('调用参数', {
            'fields': ('temperature', 'top_p', 'max_tokens'),
            'classes': ('collapse',)
        }),
        ('统计信息', {
            'fields': ('tokens', 'cost', 'cost_per_token', 'latency_display'),
            'classes': ('collapse',)
        }),
    )
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '内容'
    
    def api_response_preview(self, obj):
        if obj.api_response:
            return format_html('<pre>{}</pre>', str(obj.api_response)[:200] + '...')
        return '-'
    api_response_preview.short_description = 'API响应'
    
    def cost_per_token(self, obj):
        if obj.tokens > 0 and obj.cost:
            return f"${(obj.cost / obj.tokens):.8f}/token"
        return 'N/A'
    cost_per_token.short_description = '单token成本'
    
    def latency_display(self, obj):
        if obj.latency:
            return f"{obj.latency:.2f}秒"
        return '-'
    latency_display.short_description = '响应时间'

@admin.register(ModelUsageStat)
class ModelUsageStatAdmin(admin.ModelAdmin):
    list_display = ('model', 'date', 'call_count', 'total_tokens', 'total_cost', 'avg_cost_per_call')
    list_filter = ('model', 'date')
    readonly_fields = ('avg_cost_per_call', 'avg_tokens_per_call')
    
    def avg_cost_per_call(self, obj):
        if obj.call_count > 0:
            return f"${(obj.total_cost / obj.call_count):.6f}"
        return 'N/A'
    avg_cost_per_call.short_description = '均次调用成本'
    
    def avg_tokens_per_call(self, obj):
        if obj.call_count > 0:
            return f"{(obj.total_tokens / obj.call_count):.1f} tokens"
        return 'N/A'
    avg_tokens_per_call.short_description = '均次调用token数'