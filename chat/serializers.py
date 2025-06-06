from rest_framework import serializers
from .models import ChatConversation, ChatMessage, Application, AIModel

class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['id', 'name', 'description', 'model', 'system_role', 
                 'show_reasoning', 'created_at', 'updated_at', 'is_active']
        read_only_fields = ['created_at', 'updated_at']

class ApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['name', 'description', 'model', 'system_role', 'show_reasoning']

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['role', 'content', 'timestamp', 'tokens']

class ChatConversationSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatConversation
        fields = ['conversation_id', 'title', 'created_at', 'messages', 
                 'total_tokens', 'application']

class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(required=True)
    conversation_id = serializers.CharField(required=False)
    application_id = serializers.PrimaryKeyRelatedField(
        queryset=Application.objects.filter(is_active=True),
        required=False,
        error_messages={
            'does_not_exist': '指定应用不存在或未激活',
            'incorrect_type': '应用ID必须是数字'
        }
    )
    model_id = serializers.PrimaryKeyRelatedField(
        queryset=AIModel.objects.filter(is_active=True),
        required=False,
        error_messages={
            'does_not_exist': '指定模型不存在或未激活',
            'incorrect_type': '模型ID必须是数字'
        }
    )
    temperature = serializers.FloatField(default=0.7)
    max_tokens = serializers.IntegerField(default=512)