from django.shortcuts import render
from django.http import StreamingHttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.parsers import JSONParser
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from .models import ChatConversation, ChatMessage, AIModel, Application
from .serializers import (
    ChatRequestSerializer, ApplicationSerializer, 
    ApplicationCreateSerializer, ChatConversationSerializer
)
import json
from openai import OpenAI
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class ApplicationViewSet(ModelViewSet):
    """应用管理视图集"""
    queryset = Application.objects.filter(is_active=True)
    serializer_class = ApplicationSerializer
    
    def get_permissions(self):
        """
        根据不同的操作设置不同的权限
        - 管理员可以执行所有操作
        - 普通用户只能查看应用列表和详情
        - 未登录用户只能查看公开应用
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        根据用户权限返回不同的查询集
        - 管理员可以看到所有应用
        - 普通用户只能看到公开应用
        """
        if self.request.user.is_staff:
            return Application.objects.filter(is_active=True)
        return Application.objects.filter(is_active=True, is_public=True)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ApplicationCreateSerializer
        return ApplicationSerializer
    
    def perform_create(self, serializer):
        """创建应用时自动设置创建者"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def conversations(self, request, pk=None):
        """获取应用的对话列表"""
        application = self.get_object()
        conversations = application.conversations.all()
        serializer = ChatConversationSerializer(conversations, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """自定义详情页面的显示"""
        instance = self.get_object()
        
        # 检查是否是HTML请求
        if request.accepted_renderer.format == 'html':
            context = {
                'api_url': request.build_absolute_uri('/').rstrip('/'),
                'application_id': instance.id
            }
            return render(request, 'chat/chat_widget.html', context)
        
        # 否则返回JSON数据
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

@method_decorator(csrf_exempt, name='dispatch')
class ChatStreamView(View):
    """
    流式聊天API接口
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            print("收到的请求数据:", data)
            
            # 验证必要字段
            if not data.get('message'):
                return JsonResponse(
                    {"error": "消息内容不能为空"},
                    status=400
                )
            
            if not data.get('application_id'):
                return JsonResponse(
                    {"error": "请指定应用ID"},
                    status=400
                )
            
            # 获取应用
            try:
                application = Application.objects.get(
                    id=data['application_id'],
                    is_active=True
                )
            except Application.DoesNotExist:
                return JsonResponse(
                    {"error": "应用不存在或未激活"},
                    status=404
                )
            
            # 获取模型
            ai_model = application.model
            if not ai_model:
                return JsonResponse(
                    {"error": "应用未配置AI模型"},
                    status=400
                )
            
            # 获取或创建对话
            conversation_id = data.get('conversation_id')
            if conversation_id:
                try:
                    conversation = ChatConversation.objects.get(
                        conversation_id=conversation_id,
                        user=request.user if request.user.is_authenticated else None
                    )
                except ChatConversation.DoesNotExist:
                    return JsonResponse(
                        {"error": "会话不存在"},
                        status=404
                    )
            else:
                conversation = ChatConversation.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    application=application,
                    conversation_id=self.generate_conversation_id(),
                    title=data['message'][:50]
                )
            
            # 保存用户消息
            user_message = ChatMessage.objects.create(
                conversation=conversation,
                role='user',
                content=data['message'],
                tokens=len(data['message']) // 4
            )
            
            def event_stream():
                try:
                    client = OpenAI(
                        base_url=ai_model.api_url,
                        api_key=ai_model.api_key
                    )
                    
                    # 准备消息
                    messages = self.prepare_messages(conversation)
                    if application.system_role:
                        messages.insert(0, {
                            "role": "system",
                            "content": application.system_role
                        })
                    
                    # 创建助手消息
                    assistant_message = ChatMessage(
                        conversation=conversation,
                        role='assistant',
                        model_used=ai_model,
                        temperature=data.get('temperature', 0.7),
                        max_tokens=data.get('max_tokens', 2000)
                    )
                    
                    # 调用OpenAI API
                    response = client.chat.completions.create(
                        model=ai_model.name,
                        messages=messages,
                        stream=True,
                        temperature=data.get('temperature', 0.7),
                        max_tokens=data.get('max_tokens', 2000)
                    )
                    
                    full_response = ""
                    for chunk in response:
                        if not chunk.choices:
                            continue
                            
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            full_response += content
                            yield f"data: {json.dumps({'content': content})}\n\n"
                    
                    # 保存助手消息
                    assistant_message.content = full_response
                    assistant_message.tokens = len(full_response) // 4
                    assistant_message.save()
                    
                    # 更新对话统计
                    conversation.update_stats()
                    
                    yield "data: [DONE]\n\n"
                    
                except Exception as e:
                    error_msg = f"请求处理错误: {str(e)}"
                    print("OpenAI API错误:", error_msg)
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
            
            response = StreamingHttpResponse(
                event_stream(),
                content_type='text/event-stream'
            )
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response
            
        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "无效的JSON数据"},
                status=400
            )
        except Exception as e:
            return JsonResponse(
                {"error": str(e)},
                status=500
            )
    
    def prepare_messages(self, conversation):
        messages = []
        history_messages = conversation.messages.order_by('timestamp')[:10]
        
        for msg in history_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return messages
    
    def generate_conversation_id(self):
        import uuid
        return str(uuid.uuid4())

def chat_widget(request, application_id):
    """提供聊天组件页面"""
    try:
        application = Application.objects.get(id=application_id, is_active=True)
        context = {
            'api_url': request.build_absolute_uri('/').rstrip('/'),
            'application_id': application_id
        }
        return render(request, 'chat/chat_widget.html', context)
    except Application.DoesNotExist:
        return Response(
            {"error": "应用不存在或未激活"},
            status=status.HTTP_404_NOT_FOUND
        )