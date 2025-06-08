from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import EmbeddingModel, Knowledge, APICallLog

@admin.register(EmbeddingModel)
class EmbeddingModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'model_name', 'api_url', 'dimension', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'model_name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'model_name', 'description')
        }),
        ('API配置', {
            'fields': ('api_url', 'api_key', 'dimension', 'encoding_format')
        }),
        ('状态信息', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )

@admin.register(Knowledge)
class KnowledgeAdmin(admin.ModelAdmin):
    list_display = ('id', 'text_preview', 'model', 'similarity_score', 'is_valid', 'created_at')
    list_filter = ('model', 'is_valid', 'created_at')
    search_fields = ('text',)
    readonly_fields = ('created_at', 'updated_at', 'similarity_score')
    fieldsets = (
        ('内容信息', {
            'fields': ('text', 'model')
        }),
        ('状态信息', {
            'fields': ('similarity_score', 'is_valid', 'created_at', 'updated_at')
        }),
    )

    def text_preview(self, obj):
        """显示文本预览"""
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    text_preview.short_description = '知识内容'

@admin.register(APICallLog)
class APICallLogAdmin(admin.ModelAdmin):
    list_display = ('model', 'api_type', 'status_code', 'duration', 'created_at')
    list_filter = ('model', 'api_type', 'status_code', 'created_at')
    search_fields = ('request_data', 'response_data')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('调用信息', {
            'fields': ('model', 'api_type', 'status_code', 'duration')
        }),
        ('请求响应', {
            'fields': ('request_data', 'response_data')
        }),
        ('时间信息', {
            'fields': ('created_at',)
        }),
    )

    def has_add_permission(self, request):
        """禁止手动添加日志"""
        return False

    def has_change_permission(self, request, obj=None):
        """禁止修改日志"""
        return False