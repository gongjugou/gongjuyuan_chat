from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import Count, Sum
from django.utils.html import format_html
from .models import AIModel, ChatConversation, ChatMessage, ModelUsageStat, Application

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
    readonly_fields = ('timestamp', 'role', 'content', 'tokens', 'cost')
    fields = ('timestamp', 'role', 'content', 'model_used', 'tokens', 'cost')
    
    def has_add_permission(self, request, obj=None):
        return False

class ChatConversationInline(admin.TabularInline):
    model = ChatConversation
    extra = 0
    readonly_fields = ('conversation_id', 'title', 'created_at', 'message_count', 'total_tokens')
    fields = ('conversation_id', 'title', 'created_at', 'message_count', 'total_tokens')
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = '消息数'
    
    def has_add_permission(self, request, obj=None):
        return False

class ModelUsageStatInline(admin.TabularInline):
    model = ModelUsageStat
    extra = 0
    readonly_fields = ('date', 'call_count', 'total_tokens', 'total_cost')
    
    def has_add_permission(self, request, obj=None):
        return False

# 主管理类
@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'model', 'embedding_model', 'is_active', 'display_icon')
    list_filter = ('is_active',)
    search_fields = ('name', 'description', 'user__username')
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'user', 'is_active', 'icon_svg', 'avatar')
        }),
        ('模型设置', {
            'fields': ('model', 'embedding_model')
        }),
        ('知识库设置', {
            'fields': ('knowledge_similarity_threshold', 'max_knowledge_items'),
            'classes': ('collapse',),
            'description': '这些设置仅在选择了向量模型时生效'
        }),
        ('对话设置', {
            'fields': ('system_role',)
        })
    )
    inlines = [ChatConversationInline]
    
    def display_icon(self, obj):
        if obj.icon_svg:
            return format_html('<div style="width: 24px; height: 24px;">{}</div>', obj.icon_svg)
        elif obj.avatar:
            return format_html('<img src="{}" style="width: 24px; height: 24px; object-fit: cover;" />', obj.avatar.url)
        return '-'
    display_icon.short_description = '图标'
    
    def conversation_count(self, obj):
        return obj.conversations.count()
    conversation_count.short_description = '对话数'
    
    def total_tokens(self, obj):
        total = obj.conversations.aggregate(total=Sum('total_tokens'))['total'] or 0
        return f"{total:,} tokens"
    total_tokens.short_description = '总token数'
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            conversation_count=Count('conversations')
        )

@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'model_type', 'is_active', 'created_at')
    list_filter = ('model_type', 'is_active')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'total_usage', 'created_by')
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
        if not change:  # 只在创建新模型时设置创建人
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'application', 'model', 'total_tokens', 'total_cost', 'message_count', 'created_at')
    list_filter = ('application', 'model', 'is_active')
    search_fields = ('title', 'user__username', 'conversation_id')
    readonly_fields = ('total_tokens', 'total_cost')
    inlines = [ChatMessageInline]

    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = '消息数'

@admin.register(ModelUsageStat)
class ModelUsageStatAdmin(admin.ModelAdmin):
    list_display = ('model', 'date', 'call_count', 'total_tokens', 'total_cost')
    list_filter = ('model', 'date')
    search_fields = ('model__name',)