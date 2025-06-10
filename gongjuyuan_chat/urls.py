from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/chat/', include('chat.urls')),
]

# 在开发环境下启用静态文件和媒体文件服务
if settings.DEBUG:
    # 静态文件服务
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # 媒体文件服务
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)