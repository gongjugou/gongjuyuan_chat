from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ApplicationViewSet, ChatStreamView, chat_widget

router = DefaultRouter()
router.register(r'applications', ApplicationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('stream/', ChatStreamView.as_view(), name='chat-stream'),
    path('ui/chat/<str:application_id>/', chat_widget, name='chat-widget'),
    path('chat/<str:application_id>/', chat_widget, name='chat-interface'),
]