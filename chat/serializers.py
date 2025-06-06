from rest_framework import serializers
from .models import ChatConversation, ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['role', 'content', 'timestamp', 'tokens']

class ChatConversationSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatConversation
        fields = ['conversation_id', 'title', 'created_at', 'messages', 'total_tokens']

from .models import AIModel

class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(required=True)
    conversation_id = serializers.CharField(required=False)
    model_id = serializers.PrimaryKeyRelatedField(
        queryset=AIModel.objects.filter(is_active=True),  # 确保只查活跃模型
        required=False,
        error_messages={
            'does_not_exist': '指定模型不存在或未激活',
            'incorrect_type': '模型ID必须是数字'
        }
    )
    temperature = serializers.FloatField(default=0.7)
    max_tokens = serializers.IntegerField(default=512)