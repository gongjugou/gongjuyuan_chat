from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ApplicationViewSet, ChatStreamView, chat_widget, ChatMessageView

router = DefaultRouter()
router.register(r'applications', ApplicationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('stream/', ChatStreamView.as_view(), name='chat-stream'),
    path('ui/<str:application_id>/', chat_widget, name='chat-interface'),
    path('conversations/<str:conversation_id>/messages/', ChatMessageView.as_view(), name='chat-messages'),
]