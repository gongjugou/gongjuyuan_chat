from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import EmbeddingModel, Knowledge

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
            'fields': ('api_key', 'dimension', 'api_url', 'encoding_format')
        }),
        ('状态信息', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )

@admin.register(Knowledge)
class KnowledgeAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'answer_preview', 'model', 'is_valid', 'created_at')
    list_filter = ('model', 'is_valid', 'created_at')
    search_fields = ('question', 'answer')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('问答内容', {
            'fields': ('question', 'answer', 'model')
        }),
        ('状态信息', {
            'fields': ('is_valid', 'created_at', 'updated_at')
        }),
    )

    def answer_preview(self, obj):
        """显示答案预览"""
        return obj.answer[:100] + '...' if len(obj.answer) > 100 else obj.answer
    answer_preview.short_description = '答案预览'