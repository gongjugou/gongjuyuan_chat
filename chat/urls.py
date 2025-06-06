from django.urls import path
from .views import ChatStreamView

urlpatterns = [
    path('stream/', ChatStreamView.as_view(), name='chat-stream'),
]