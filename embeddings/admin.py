from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import EmbeddingModel, Knowledge, APICallLog
from .services import EmbeddingService

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
    readonly_fields = ('embedding', 'created_at', 'updated_at', 'similarity_score')
    actions = ['regenerate_embeddings']
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

    def save_model(self, request, obj, form, change):
        """保存模型时自动生成向量"""
        # 检查是否需要生成向量
        if not change or 'text' in form.changed_data or 'model' in form.changed_data:
            try:
                # 创建向量服务
                service = EmbeddingService(obj.model)
                # 获取向量
                embedding_array = service.get_embedding(obj.text)
                # 设置向量
                obj.set_embedding_array(embedding_array)
            except Exception as e:
                self.message_user(request, f"生成向量失败: {str(e)}", level='error')
                return
        
        super().save_model(request, obj, form, change)
        
    def regenerate_embeddings(self, request, queryset):
        """重新生成选中知识的向量"""
        success_count = 0
        error_count = 0
        
        for obj in queryset:
            try:
                # 创建向量服务
                service = EmbeddingService(obj.model)
                # 获取向量
                embedding_array = service.get_embedding(obj.text)
                # 设置向量
                obj.set_embedding_array(embedding_array)
                obj.save()
                success_count += 1
            except Exception as e:
                error_count += 1
                self.message_user(request, f"知识 {obj.id} 重新生成向量失败: {str(e)}", level='error')
        
        if success_count > 0:
            self.message_user(request, f"成功重新生成 {success_count} 条知识的向量")
        if error_count > 0:
            self.message_user(request, f"重新生成向量失败: {error_count} 条", level='error')
    regenerate_embeddings.short_description = "重新生成向量"

@admin.register(APICallLog)
class APICallLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'model', 'api_type', 'status_code', 'duration', 'created_at')
    list_filter = ('model', 'api_type', 'status_code')
    readonly_fields = ('model', 'api_type', 'request_data', 'response_data', 'status_code', 'duration', 'created_at')

    def has_add_permission(self, request):
        """禁止手动添加日志"""
        return False

    def has_change_permission(self, request, obj=None):
        """禁止修改日志"""
        return False