from rest_framework import serializers
from .models import Application, ChatConversation, ChatMessage, AIModel
import logging
import traceback

logger = logging.getLogger(__name__)

class AIModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIModel
        fields = ['id', 'name', 'model_type', 'max_tokens_limit', 'description']

class ApplicationSerializer(serializers.ModelSerializer):
    model = AIModelSerializer(read_only=True)
    
    class Meta:
        model = Application
        fields = [
            'id', 'name', 'description', 'model', 
            'system_role', 'show_reasoning', 'is_public'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class ApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['name', 'description', 'model', 'system_role', 'show_reasoning']

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'role', 'content', 'reasoning', 'timestamp', 
            'tokens', 'cost', 'model_used', 'temperature',
            'top_p', 'max_tokens'
        ]
        read_only_fields = [
            'id', 'timestamp', 'tokens', 'cost', 
            'model_used', 'temperature', 'top_p', 'max_tokens'
        ]

class ChatConversationSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    model = AIModelSerializer(read_only=True)
    
    class Meta:
        model = ChatConversation
        fields = [
            'id', 'conversation_id', 'title', 'session_id',
            'model', 'created_at', 'updated_at', 'messages',
            'total_tokens', 'total_cost', 'temperature', 'top_p'
        ]
        read_only_fields = [
            'id', 'conversation_id', 'created_at', 'updated_at',
            'total_tokens', 'total_cost'
        ]
    
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