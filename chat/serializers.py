from rest_framework import serializers
from .models import ChatConversation, ChatMessage, Application, AIModel
import logging
import traceback

logger = logging.getLogger(__name__)

class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['id', 'name', 'description', 'system_role', 'show_reasoning', 'is_public']
        read_only_fields = ['id']

class ApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['name', 'description', 'model', 'system_role', 'show_reasoning']

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['role', 'content', 'timestamp']
        read_only_fields = ['timestamp']

class ChatConversationSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatConversation
        fields = ['conversation_id', 'title', 'created_at', 'messages', 
                 'total_tokens', 'application', 'session_id']
        read_only_fields = ['conversation_id', 'created_at', 'total_tokens']
    
    def to_representation(self, instance):
        """自定义序列化输出"""
        try:
            data = super().to_representation(instance)
            # 确保application字段只返回ID
            if 'application' in data and data['application']:
                data['application'] = instance.application.id
            # 确保session_id字段存在
            if not data.get('session_id'):
                data['session_id'] = instance.session_id
            return data
        except Exception as e:
            logger.error(f"序列化对话时发生错误: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise

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