from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import AIModel

@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'model_type', 'is_active', 'created_at')
    list_filter = ('model_type', 'is_active')
    search_fields = ('name', 'description')
    fieldsets = (
        ('基本信息', {
            'fields': ( 'name', 'model_type', 'is_active', 'description')
        }),
        ('API配置', {
            'fields': ('api_url', 'api_key'),
            'classes': ('collapse',)
        }),
        ('元数据', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ('created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # 如果是新建而不是更新
            obj.created_by = request.user
        super().save_model(request, obj, form, change)