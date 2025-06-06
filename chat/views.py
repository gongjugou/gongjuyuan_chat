from django.shortcuts import render

# Create your views here.
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ChatConversation, ChatMessage, AIModel
from .serializers import ChatRequestSerializer
import json
from openai import OpenAI
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatStreamView(APIView):
    """
    流式聊天API接口
    """
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        ai_model = serializer.validated_data.get('model_id') or \
                  AIModel.objects.filter(is_active=True).first()
        user = request.user if request.user.is_authenticated else None
        message = serializer.validated_data['message']
        conversation_id = serializer.validated_data.get('conversation_id')
        
        # 获取或创建对话
        if conversation_id:
            conversation = ChatConversation.objects.get(
                conversation_id=conversation_id,
                user=user
            )
        else:
            conversation = ChatConversation.objects.create(
                user=user,
                conversation_id=self.generate_conversation_id(),
                title=message[:50]
            )
        
        # 保存用户消息
        user_message = ChatMessage.objects.create(
            conversation=conversation,
            role='user',
            content=message,
            tokens=len(message) // 4  # 简单估算token数
        )
        
        # 获取活跃的AI模型
        ai_model = AIModel.objects.filter(
            model_type='LLM', 
            is_active=True
        ).first()
        
        if not ai_model:
            return Response(
                {"error": "请指定模型或设置默认活跃模型"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 创建流式响应
        def event_stream():
            # 首先保存assistant消息记录
            assistant_message = ChatMessage(
                conversation=conversation,
                role='assistant',
                model_used=ai_model,
                temperature=serializer.validated_data['temperature'],
                max_tokens=serializer.validated_data['max_tokens']
            )
            
            # 初始化 OpenAI 客户端
            client = OpenAI(
                base_url=ai_model.api_url,
                api_key=ai_model.api_key
            )
            
            # 准备消息
            messages = self.prepare_messages(conversation)
            
            try:
                # 发送流式请求
                response = client.chat.completions.create(
                    model=ai_model.name,
                    messages=messages,
                    stream=True,
                    temperature=serializer.validated_data['temperature'],
                    max_tokens=serializer.validated_data['max_tokens']
                )
                
                full_response = ""
                for chunk in response:
                    if not chunk.choices:
                        continue
                        
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield f"data: {json.dumps({'content': content})}\n\n"
                    if chunk.choices[0].delta.reasoning_content:
                        content = chunk.choices[0].delta.reasoning_content
                        full_response += content
                        yield f"data: {json.dumps({'content': content})}\n\n"
                
                # 保存完整的助手回复
                assistant_message.content = full_response
                assistant_message.tokens = len(full_response) // 4  # 估算token
                assistant_message.save()
                
                # 更新会话统计
                conversation.update_stats()
                
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                error_msg = f"请求处理错误: {str(e)}"
                print(error_msg)  # 添加日志
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                return
        
        return StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
    
    def prepare_messages(self, conversation):
        """准备历史消息上下文"""
        messages = []
        history_messages = conversation.messages.order_by('timestamp')[:10]  # 限制历史消息数量
        
        for msg in history_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return messages
    
    def generate_conversation_id(self):
        """生成唯一的对话ID"""
        import uuid
        return str(uuid.uuid4())