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
    ApplicationCreateSerializer, ChatConversationSerializer,
    ChatMessageSerializer
)
import json
from openai import OpenAI
from django.contrib.auth import get_user_model
from django.conf import settings
import time
import logging
import traceback
import uuid

User = get_user_model()
logger = logging.getLogger(__name__)

class ApplicationViewSet(ModelViewSet):
    """应用管理视图集"""
    queryset = Application.objects.all()
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
        try:
            logger.info(f"开始获取对话列表 - 应用ID: {pk}")
            application = self.get_object()
            logger.info(f"找到应用: {application.name}")
            
            session_id = request.query_params.get('session_id')
            logger.info(f"会话ID: {session_id}")
            
            if not session_id:
                logger.warning("未提供会话ID")
                return Response([], status=status.HTTP_200_OK)
            
            try:
                # 使用 application.conversations 反向关系查询
                conversations = application.conversations.filter(
                    session_id=session_id,
                    is_active=True
                ).order_by('-updated_at')
                
                logger.info(f"找到 {conversations.count()} 个对话")
                for conv in conversations:
                    logger.info(f"对话ID: {conv.conversation_id}, 标题: {conv.title}, 会话ID: {conv.session_id}")
                
                # 检查序列化器
                try:
                    serializer = ChatConversationSerializer(conversations, many=True)
                    data = serializer.data
                    logger.info(f"序列化后的数据: {data}")
                    return Response(data)
                except Exception as e:
                    logger.error(f"序列化数据时发生错误: {str(e)}")
                    error_stack = traceback.format_exc()
                    logger.error(f"错误堆栈: {error_stack}")
                    return Response(
                        {
                            "error": "序列化数据时发生错误",
                            "detail": str(e),
                            "stack": error_stack
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
            except Exception as e:
                logger.error(f"查询对话时发生错误: {str(e)}")
                error_stack = traceback.format_exc()
                logger.error(f"错误堆栈: {error_stack}")
                return Response(
                    {
                        "error": "查询对话时发生错误",
                        "detail": str(e),
                        "stack": error_stack
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
        except Application.DoesNotExist:
            logger.error(f"应用不存在: {pk}")
            return Response(
                {"error": "应用不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"获取对话列表时发生错误: {str(e)}")
            error_stack = traceback.format_exc()
            logger.error(f"错误堆栈: {error_stack}")
            return Response(
                {
                    "error": "获取对话列表时发生错误",
                    "detail": str(e),
                    "stack": error_stack
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
        start_time = time.time()
        logger.info(f"开始处理请求: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            logger.info(f"收到聊天请求 - 会话ID: {session_id}")
            
            # 验证应用
            application_id = data.get('application_id')
            try:
                application = Application.objects.get(id=application_id, is_active=True)
                logger.info(f"找到应用: {application.name}")
            except Application.DoesNotExist:
                logger.error(f"应用不存在: {application_id}")
                return JsonResponse(
                    {"error": "应用不存在或未激活"},
                    status=404
                )
            
            # 获取或创建对话
            conversation_id = data.get('conversation_id')
            if conversation_id:
                try:
                    conversation = ChatConversation.objects.get(
                        conversation_id=conversation_id,
                        session_id=session_id
                    )
                    logger.info(f"找到现有对话: {conversation.title}")
                except ChatConversation.DoesNotExist:
                    logger.error(f"对话不存在: {conversation_id}")
                    return JsonResponse(
                        {"error": "会话不存在"},
                        status=404
                    )
            else:
                conversation = ChatConversation.objects.create(
                    session_id=session_id,
                    application=application,
                    conversation_id=self.generate_conversation_id(),
                    title=data['message'][:50],
                    model=application.model
                )
                logger.info(f"创建新对话: {conversation.title}")
            
            logger.info(f"获取/创建对话耗时: {time.time() - start_time:.2f}秒")
            
            # 保存用户消息
            user_message = ChatMessage.objects.create(
                conversation=conversation,
                role='user',
                content=data['message'],
                tokens=len(data['message']) // 4,
                model_used=application.model  # 设置消息使用的模型
            )
            logger.info(f"保存用户消息完成: {user_message.id}")
            
            def event_stream():
                stream_start_time = time.time()
                logger.info(f"开始流式响应: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                try:
                    client = OpenAI(
                        base_url=application.model.api_url,
                        api_key=application.model.api_key
                    )
                    logger.info(f"OpenAI客户端初始化完成，API URL: {application.model.api_url}")
                    
                    # 准备消息
                    messages = self.prepare_messages(conversation)
                    if application.system_role:
                        messages.insert(0, {
                            "role": "system",
                            "content": application.system_role
                        })
                    
                    logger.info(f"准备消息耗时: {time.time() - stream_start_time:.2f}秒")
                    logger.info(f"发送到OpenAI的消息: {messages}")
                    
                    # 创建助手消息
                    assistant_message = ChatMessage(
                        conversation=conversation,
                        role='assistant',
                        model_used=application.model,
                        temperature=data.get('temperature', 0.7),
                        max_tokens=data.get('max_tokens', 2000)
                    )
                    
                    # 调用OpenAI API
                    api_start_time = time.time()
                    logger.info(f"开始调用OpenAI API: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    try:
                        response = client.chat.completions.create(
                            model=application.model.name,
                            messages=messages,
                            stream=True,
                            temperature=data.get('temperature', 0.7),
                            max_tokens=data.get('max_tokens', 2000)
                        )
                        logger.info(f"OpenAI API调用成功，开始接收流式响应")
                    except Exception as e:
                        logger.error(f"OpenAI API调用失败: {str(e)}")
                        yield f"data: {json.dumps({'error': f'OpenAI API调用失败: {str(e)}'})}\n\n"
                        return
                    
                    logger.info(f"OpenAI API调用耗时: {time.time() - api_start_time:.2f}秒")
                    
                    full_response = ""
                    first_chunk_time = None
                    chunk_count = 0
                    
                    try:
                        for chunk in response:
                            logger.debug(f"收到原始响应块: {chunk}")
                            
                            if not chunk.choices:
                                logger.warning("收到空的choices")
                                continue
                                
                            # 检查是否有 reasoning_content
                            if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                                content = chunk.choices[0].delta.reasoning_content
                                response_data = json.dumps({'reasoning_content': content})
                                logger.debug(f"发送思考过程数据: {response_data}")
                                yield f"data: {response_data}\n\n"
                            # 检查是否有 content
                            elif hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                                content = chunk.choices[0].delta.content
                                response_data = json.dumps({'content': content})
                                logger.debug(f"发送回答数据: {response_data}")
                                yield f"data: {response_data}\n\n"
                            else:
                                logger.warning("响应块没有有效内容")
                                continue
                                
                            if not content:
                                logger.warning("收到空的content")
                                continue
                                
                            if first_chunk_time is None:
                                first_chunk_time = time.time()
                                logger.info(f"收到第一个响应块耗时: {first_chunk_time - api_start_time:.2f}秒")
                            
                            full_response += content
                            chunk_count += 1
                            logger.info(f"发送响应块 {chunk_count}: {content}")
                            
                    except Exception as e:
                        logger.error(f"处理流式响应时出错: {str(e)}")
                        yield f"data: {json.dumps({'error': f'处理响应时出错: {str(e)}'})}\n\n"
                        return
                    
                    if not full_response:
                        logger.error("没有收到任何有效响应")
                        yield f"data: {json.dumps({'error': '没有收到任何有效响应'})}\n\n"
                        return
                    
                    # 保存助手消息
                    assistant_message.content = full_response
                    assistant_message.tokens = len(full_response) // 4
                    assistant_message.save()
                    
                    # 更新对话统计
                    conversation.update_stats()
                    
                    logger.info(f"完整响应处理耗时: {time.time() - stream_start_time:.2f}秒")
                    logger.info(f"总响应长度: {len(full_response)} 字符")
                    logger.info(f"总响应块数: {chunk_count}")
                    
                    yield "data: [DONE]\n\n"
                    
                except Exception as e:
                    error_msg = f"请求处理错误: {str(e)}"
                    logger.error(f"OpenAI API错误: {error_msg}")
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
            
            response = StreamingHttpResponse(
                event_stream(),
                content_type='text/event-stream'
            )
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response
            
        except json.JSONDecodeError:
            logger.error("无效的JSON数据")
            return JsonResponse(
                {"error": "无效的JSON数据"},
                status=400
            )
        except Exception as e:
            logger.error(f"处理请求时发生错误: {str(e)}")
            return JsonResponse(
                {"error": str(e)},
                status=500
            )
    
    def prepare_messages(self, conversation):
        """准备发送给OpenAI的消息列表"""
        messages = []
        
        # 添加系统消息（如果有）
        if conversation.application and conversation.application.system_role:
            messages.append({
                "role": "system",
                "content": conversation.application.system_role
            })
        
        # 如果是新对话，直接返回系统消息
        if not conversation.messages.exists():
            return messages
        
        # 获取最近的对话历史，包括最新的消息
        history_messages = conversation.messages.order_by('-timestamp')[:10]
        history_messages = list(reversed(history_messages))  # 反转顺序，确保按时间顺序排列
        
        # 添加历史消息
        for msg in history_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        logger.info(f"准备的消息列表: {messages}")
        return messages
    
    def generate_conversation_id(self):
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

class ChatMessageView(APIView):
    """处理聊天消息的视图"""
    permission_classes = [AllowAny]
    
    def get(self, request, conversation_id):
        try:
            session_id = request.query_params.get('session_id')
            logger.info(f"获取消息历史 - 对话ID: {conversation_id}, 会话ID: {session_id}")
            
            if not session_id:
                logger.warning("未提供会话ID")
                return Response(
                    {"error": "需要提供会话ID"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            conversation = ChatConversation.objects.get(
                conversation_id=conversation_id,
                session_id=session_id
            )
            
            messages = conversation.messages.all().order_by('timestamp')
            logger.info(f"找到 {messages.count()} 条消息")
            
            serializer = ChatMessageSerializer(messages, many=True)
            return Response(serializer.data)
            
        except ChatConversation.DoesNotExist:
            logger.error(f"对话不存在: {conversation_id}")
            return Response(
                {"error": "对话不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"获取消息历史时发生错误: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )