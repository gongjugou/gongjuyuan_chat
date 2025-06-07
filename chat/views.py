from django.shortcuts import render, get_object_or_404
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
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
from django.views.generic import TemplateView
from datetime import datetime
from wsgiref.util import FileWrapper
import io
from django.http import Http404

User = get_user_model()
logger = logging.getLogger(__name__)

class ApplicationViewSet(ModelViewSet):
    """应用管理视图集"""
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [AllowAny]
    
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

    @action(detail=True, methods=['post'])
    def create_conversation(self, request, pk=None):
        """创建新对话"""
        try:
            logger.info(f"开始创建新对话 - 应用ID: {pk}")
            application = self.get_object()
            logger.info(f"找到应用: {application.name}")
            
            session_id = request.data.get('session_id')
            user_message = request.data.get('message')
            logger.info(f"会话ID: {session_id}")
            
            if not session_id:
                logger.warning("未提供会话ID")
                return Response(
                    {"error": "需要提供会话ID"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                # 获取或创建对话
                conv_start = time.time()
                conversation_id = request.data.get('conversation_id')
                if conversation_id:
                    try:
                        conversation = ChatConversation.objects.select_related('model').get(
                            conversation_id=conversation_id,
                            session_id=session_id,
                            application=application
                        )
                        print(f"\n[3/7] 查询现有对话: {time.time() - conv_start:.3f}秒")
                        print(f"对话ID: {conversation.conversation_id}")
                        print(f"对话标题: {conversation.title}")
                    except ChatConversation.DoesNotExist:
                        return JsonResponse(
                            {"error": "会话不存在"},
                            status=404
                        )
                else:
                    # 使用用户消息作为标题
                    title = user_message[:50] if user_message else '新对话'
                    conversation = ChatConversation.objects.create(
                        session_id=session_id,
                        application=application,
                        conversation_id=str(uuid.uuid4()),
                        title=title,  # 使用用户消息作为标题
                        model=application.model
                    )
                    print(f"\n[3/7] 创建新对话: {time.time() - conv_start:.3f}秒")
                    print(f"对话ID: {conversation.conversation_id}")
                    print(f"对话标题: {conversation.title}")
                
                # 保存用户消息
                msg_start = time.time()
                user_message_obj = ChatMessage.objects.create(
                    conversation=conversation,
                    role='user',
                    content=user_message,
                    tokens=len(user_message) // 4,
                    model_used=application.model
                )
                print(f"\n[4/7] 保存用户消息: {time.time() - msg_start:.3f}秒")
                print(f"消息ID: {user_message_obj.id}")
                print(f"消息内容: {user_message[:50]}...")
                
                def event_stream():
                    stream_start = time.time()
                    print(f"\n[5/7] 开始流式处理: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    try:
                        # 初始化OpenAI客户端
                        client_start = time.time()
                        client = OpenAI(
                            base_url=application.model.api_url,
                            api_key=application.model.api_key
                        )
                        print(f"初始化OpenAI客户端: {time.time() - client_start:.3f}秒")
                        
                        # 准备消息
                        msg_prep_start = time.time()
                        messages = []
                        if application.system_role:
                            messages.append({
                                "role": "system",
                                "content": application.system_role
                            })
                        
                        # 获取历史消息（只获取用户和助手的消息）
                        history_start = time.time()
                        history_messages = conversation.messages.filter(
                            role__in=['user', 'assistant'],
                            conversation=conversation  # 确保只获取当前对话的消息
                        ).order_by('-timestamp')[:5]
                        for msg in reversed(history_messages):
                            if msg.role in ['user', 'assistant']:  # 确保只添加用户和助手的消息
                                messages.append({
                                    "role": msg.role,
                                    "content": msg.content
                                })
                        print(f"准备历史消息: {time.time() - history_start:.3f}秒")
                        print(f"总消息准备: {time.time() - msg_prep_start:.3f}秒")
                        print(f"历史消息数量: {len(history_messages)}")
                        
                        # 创建助手消息
                        assistant_start = time.time()
                        assistant_message = ChatMessage(
                            conversation=conversation,
                            role='assistant',
                            model_used=application.model,
                            temperature=request.data.get('temperature', 0.7),
                            max_tokens=request.data.get('max_tokens', 2000)
                        )
                        print(f"创建助手消息对象: {time.time() - assistant_start:.3f}秒")
                        
                        # 调用OpenAI API
                        api_start = time.time()
                        print(f"\n[6/7] 开始调用OpenAI API: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                        response = client.chat.completions.create(
                            model=application.model.name,
                            messages=messages,
                            stream=True,
                            temperature=0.7,  # 使用默认值
                            max_tokens=2000   # 使用默认值
                        )
                        print(f"API调用耗时: {time.time() - api_start:.3f}秒")
                        
                        full_response = ""
                        first_chunk_time = None
                        chunk_count = 0
                        total_chunk_time = 0
                        
                        # 处理流式响应
                        stream_process_start = time.time()
                        print("\n[7/7] 开始接收流式响应:")
                        for chunk in response:
                            chunk_start = time.time()
                            if not chunk.choices:
                                continue
                                
                            if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                                content = chunk.choices[0].delta.reasoning_content
                                yield f"data: {json.dumps({'reasoning_content': content})}\n\n"
                            elif hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                                content = chunk.choices[0].delta.content
                                yield f"data: {json.dumps({'content': content})}\n\n"
                                full_response += content
                                
                                if first_chunk_time is None:
                                    first_chunk_time = time.time()
                                    print(f"收到第一个响应块: {first_chunk_time - api_start:.3f}秒")
                                
                                chunk_count += 1
                                chunk_time = time.time() - chunk_start
                                total_chunk_time += chunk_time
                                if chunk_count % 10 == 0:  # 每10个块记录一次
                                    print(f"处理第{chunk_count}个响应块: {chunk_time:.3f}秒")
                        
                        print(f"\n流式响应处理完成:")
                        print(f"总耗时: {time.time() - stream_process_start:.3f}秒")
                        print(f"平均每块耗时: {total_chunk_time/chunk_count if chunk_count > 0 else 0:.3f}秒")
                        
                        # 保存助手消息
                        save_start = time.time()
                        assistant_message.content = full_response
                        assistant_message.tokens = len(full_response) // 4
                        assistant_message.save()
                        print(f"保存助手消息: {time.time() - save_start:.3f}秒")
                        
                        # 更新对话统计
                        stats_start = time.time()
                        conversation.update_stats()
                        print(f"更新对话统计: {time.time() - stats_start:.3f}秒")
                        
                        print(f"\n流式处理完成:")
                        print(f"总耗时: {time.time() - stream_start:.3f}秒")
                        print(f"总响应长度: {len(full_response)} 字符")
                        print(f"总响应块数: {chunk_count}")
                        
                        yield "data: [DONE]\n\n"
                        
                    except Exception as e:
                        print(f"\n流式处理出错: {str(e)}")
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
                
                response = StreamingHttpResponse(
                    event_stream(),
                    content_type='text/event-stream'
                )
                response['Cache-Control'] = 'no-cache'
                response['X-Accel-Buffering'] = 'no'
                
                print(f"\n请求处理完成:")
                print(f"总耗时: {time.time() - stream_start:.3f}秒")
                print("="*50 + "\n")
                return response
                
            except Exception as e:
                logger.error(f"创建对话时发生错误: {str(e)}")
                error_stack = traceback.format_exc()
                logger.error(f"错误堆栈: {error_stack}")
                return Response(
                    {
                        "error": "创建对话时发生错误",
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
            logger.error(f"创建对话时发生错误: {str(e)}")
            error_stack = traceback.format_exc()
            logger.error(f"错误堆栈: {error_stack}")
            return Response(
                {
                    "error": "创建对话时发生错误",
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
        print("\n" + "="*50)
        print(f"开始处理请求: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50)
        
        try:
            # 解析请求数据
            parse_start = time.time()
            data = json.loads(request.body)
            session_id = data.get('session_id')
            application_id = data.get('application_id')
            print(f"\n[1/7] 解析请求数据: {time.time() - parse_start:.3f}秒")
            print(f"会话ID: {session_id}")
            print(f"应用ID: {application_id}")
            
            # 验证应用
            app_start = time.time()
            try:
                application = Application.objects.select_related('model').get(id=application_id, is_active=True)
                print(f"\n[2/7] 查询应用: {time.time() - app_start:.3f}秒")
                print(f"应用名称: {application.name}")
                print(f"模型名称: {application.model.name}")
            except Application.DoesNotExist:
                return JsonResponse(
                    {"error": "应用不存在或未激活"},
                    status=404
                )
            
            # 获取或创建对话
            conv_start = time.time()
            conversation_id = data.get('conversation_id')
            if conversation_id:
                try:
                    conversation = ChatConversation.objects.select_related('model').get(
                        conversation_id=conversation_id,
                        session_id=session_id,
                        application=application
                    )
                    print(f"\n[3/7] 查询现有对话: {time.time() - conv_start:.3f}秒")
                    print(f"对话ID: {conversation.conversation_id}")
                    print(f"对话标题: {conversation.title}")
                except ChatConversation.DoesNotExist:
                    return JsonResponse(
                        {"error": "会话不存在"},
                        status=404
                    )
            else:
                # 使用用户消息作为标题
                title = data['message'][:50] if data['message'] else '新对话'
                conversation = ChatConversation.objects.create(
                    session_id=session_id,
                    application=application,
                    conversation_id=str(uuid.uuid4()),
                    title=title,  # 使用用户消息作为标题
                    model=application.model
                )
                print(f"\n[3/7] 创建新对话: {time.time() - conv_start:.3f}秒")
                print(f"对话ID: {conversation.conversation_id}")
                print(f"对话标题: {conversation.title}")
            
            # 保存用户消息
            msg_start = time.time()
            user_message = ChatMessage.objects.create(
                conversation=conversation,
                role='user',
                content=data['message'],
                tokens=len(data['message']) // 4,
                model_used=application.model
            )
            print(f"\n[4/7] 保存用户消息: {time.time() - msg_start:.3f}秒")
            print(f"消息ID: {user_message.id}")
            print(f"消息内容: {data['message'][:50]}...")
            
            def event_stream():
                stream_start = time.time()
                print(f"\n[5/7] 开始流式处理: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                try:
                    # 初始化OpenAI客户端
                    client_start = time.time()
                    client = OpenAI(
                        base_url=application.model.api_url,
                        api_key=application.model.api_key
                    )
                    print(f"初始化OpenAI客户端: {time.time() - client_start:.3f}秒")
                    
                    # 准备消息
                    msg_prep_start = time.time()
                    messages = []
                    if application.system_role:
                        messages.append({
                            "role": "system",
                            "content": "你是一个智能助手，可以帮助用户解答问题。请保持友好和专业的态度。"
                        })
                    
                    # 获取历史消息
                    history_messages = conversation.messages.filter(
                        role__in=['user', 'assistant']
                    ).order_by('-timestamp')[:5]
                    
                    # 添加历史消息（按时间正序）
                    for msg in reversed(history_messages):
                        messages.append({
                            "role": msg.role,
                            "content": msg.content
                        })
                    
                    # 添加当前用户消息
                    messages.append({
                        "role": "user",
                        "content": data.get('message', '')
                    })

                    # 调用OpenAI API
                    api_start = time.time()
                    print(f"\n[6/7] 开始调用OpenAI API: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    response = client.chat.completions.create(
                        model=application.model.name,
                        messages=messages,
                        stream=True,
                        temperature=0.7,  # 使用默认值
                        max_tokens=2000   # 使用默认值
                    )

                    # 记录第一个响应块的时间
                    first_chunk_time = None
                    total_chunks = 0
                    total_content_length = 0
                    full_response = ""
                    full_reasoning = ""

                    # 逐步接收并处理响应
                    print("[yellow]开始接收响应...[/]")
                    for chunk in response:
                        if not chunk.choices:
                            continue
                        
                        # 记录第一个响应块的时间
                        if first_chunk_time is None:
                            first_chunk_time = time.time()
                            print(f"第一个响应块耗时: {first_chunk_time - api_start:.3f}秒")
                        
                        total_chunks += 1
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            total_content_length += len(content)
                            full_response += content
                            # 直接yield数据
                            yield f"data: {json.dumps({'content': content})}\n\n"
                        if chunk.choices[0].delta.reasoning_content:
                            content = chunk.choices[0].delta.reasoning_content
                            total_content_length += len(content)
                            full_reasoning += content
                            yield f"data: {json.dumps({'reasoning_content': content})}\n\n"

                    # 保存助手消息
                    assistant_message = ChatMessage.objects.create(
                        conversation=conversation,
                        role='assistant',
                        content=full_response,
                        reasoning=full_reasoning,
                        tokens=len(full_response) // 4,
                        model_used=application.model
                    )

                    # 更新对话统计
                    conversation.update_stats()

                    # 记录结束时间和统计信息
                    end_time = time.time()
                    print(f"\n[bold green]执行完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]")
                    print(f"[bold cyan]性能统计:[/]")
                    print(f"[dim]总执行时间: {round(end_time - start_time, 3)} 秒[/]")
                    print(f"[dim]API请求总耗时: {round(end_time - api_start, 3)} 秒[/]")
                    print(f"[dim]总响应块数: {total_chunks}[/]")
                    print(f"[dim]总内容长度: {total_content_length} 字符[/]")
                    if total_chunks > 0:
                        print(f"[dim]平均每块耗时: {round((end_time - first_chunk_time) / total_chunks, 3)} 秒[/]")
                        print(f"[dim]平均每字符耗时: {round((end_time - first_chunk_time) / total_content_length, 3)} 秒[/]")

                    yield "data: [DONE]\n\n"

                except Exception as e:
                    print(f"\n流式处理出错: {str(e)}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

            response = StreamingHttpResponse(
                event_stream(),
                content_type='text/event-stream'
            )
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            
            return response

        except json.JSONDecodeError:
            print("\nJSON解析错误")
            return JsonResponse(
                {"error": "无效的JSON数据"},
                status=400
            )
        except Exception as e:
            print(f"\n请求处理错误: {str(e)}")
            return JsonResponse(
                {"error": str(e)},
                status=500
            )

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

class ApplicationDetailView(APIView):
    """获取应用详情"""
    permission_classes = [AllowAny]
    
    def get(self, request, application_id):
        try:
            application = get_object_or_404(Application, id=application_id, is_active=True)
            serializer = ApplicationSerializer(application)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"获取应用详情失败: {str(e)}")
            return Response(
                {"error": "获取应用详情失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ApplicationListView(APIView):
    """获取应用列表"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            applications = Application.objects.filter(is_active=True, is_public=True)
            serializer = ApplicationSerializer(applications, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"获取应用列表失败: {str(e)}")
            return Response(
                {"error": "获取应用列表失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ConversationListView(APIView):
    """对话列表管理"""
    permission_classes = [AllowAny]
    
    def get(self, request, application_id):
        """获取对话列表"""
        try:
            session_id = request.GET.get('session_id')
            if not session_id:
                return Response(
                    {"error": "缺少session_id参数"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            application = get_object_or_404(Application, id=application_id, is_active=True)
            conversations = ChatConversation.objects.filter(
                application=application,
                session_id=session_id,
                is_active=True
            ).order_by('-updated_at')
            
            serializer = ChatConversationSerializer(conversations, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"获取对话列表失败: {str(e)}")
            return Response(
                {"error": "获取对话列表失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request, application_id):
        """创建新对话"""
        try:
            session_id = request.data.get('session_id')
            if not session_id:
                return Response(
                    {"error": "缺少session_id参数"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            application = get_object_or_404(Application, id=application_id, is_active=True)
            conversation = ChatConversation.objects.create(
                application=application,
                session_id=session_id,
                conversation_id=str(uuid.uuid4()),
                title=request.data.get('title', '新对话'),
                model=application.model
            )
            
            serializer = ChatConversationSerializer(conversation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"创建对话失败: {str(e)}")
            return Response(
                {"error": "创建对话失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ConversationDetailView(APIView):
    """对话详情管理"""
    permission_classes = [AllowAny]
    
    def get(self, request, application_id, conversation_id):
        """获取对话详情"""
        try:
            session_id = request.GET.get('session_id')
            if not session_id:
                return Response(
                    {"error": "缺少session_id参数"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            application = get_object_or_404(Application, id=application_id, is_active=True)
            conversation = get_object_or_404(
                ChatConversation,
                application=application,
                conversation_id=conversation_id,
                session_id=session_id,
                is_active=True
            )
            
            serializer = ChatConversationSerializer(conversation)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"获取对话详情失败: {str(e)}")
            return Response(
                {"error": "获取对话详情失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, application_id, conversation_id):
        """删除对话"""
        try:
            session_id = request.GET.get('session_id')
            if not session_id:
                return Response(
                    {"error": "缺少session_id参数"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            application = get_object_or_404(Application, id=application_id, is_active=True)
            conversation = get_object_or_404(
                ChatConversation,
                application=application,
                conversation_id=conversation_id,
                session_id=session_id,
                is_active=True
            )
            
            conversation.is_active = False
            conversation.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"删除对话失败: {str(e)}")
            return Response(
                {"error": "删除对话失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MessageListView(APIView):
    """消息列表管理"""
    permission_classes = [AllowAny]
    
    def get(self, request, application_id, conversation_id):
        """获取消息历史"""
        try:
            session_id = request.GET.get('session_id')
            if not session_id:
                return Response(
                    {"error": "缺少session_id参数"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            application = get_object_or_404(Application, id=application_id, is_active=True)
            conversation = get_object_or_404(
                ChatConversation,
                application=application,
                conversation_id=conversation_id,
                session_id=session_id,
                is_active=True
            )
            
            messages = conversation.messages.all().order_by('timestamp')
            serializer = ChatMessageSerializer(messages, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"获取消息历史失败: {str(e)}")
            return Response(
                {"error": "获取消息历史失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(csrf_exempt, name='dispatch')
class MessageStreamView(View):
    """流式消息处理"""
    permission_classes = [AllowAny]
    
    def post(self, request, application_id, conversation_id):
        start_time = time.time()
        print("\n" + "="*50)
        print(f"开始执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50)
        
        try:
            # 解析请求数据
            data = json.loads(request.body)
            session_id = data.get('session_id')
            user_message = data.get('message')
            
            if not session_id:
                return JsonResponse(
                    {"error": "缺少session_id参数"},
                    status=400
                )

            # 查询应用和对话
            application = get_object_or_404(Application, id=application_id, is_active=True)
            conversation = get_object_or_404(
                ChatConversation,
                application=application,
                conversation_id=conversation_id,
                session_id=session_id,
                is_active=True
            )

            # 保存用户消息
            user_message_obj = ChatMessage.objects.create(
                conversation=conversation,
                role='user',
                content=user_message,
                tokens=len(user_message) // 4,
                model_used=application.model
            )

            def event_stream():
                try:
                    # 初始化OpenAI客户端
                    client_init_start = time.time()
                    client = OpenAI(
                        base_url=application.model.api_url,
                        api_key=application.model.api_key
                    )
                    print(f"客户端初始化耗时: {time.time() - client_init_start:.3f}秒")

                    # 准备消息
                    messages = []
                    # 添加系统角色消息
                    if application.system_role:
                        messages.append({
                            "role": "system",
                            "content": "你是一个智能助手，可以帮助用户解答问题。请保持友好和专业的态度。"
                        })
                    
                    # 获取历史消息
                    history_messages = conversation.messages.filter(
                        role__in=['user', 'assistant']
                    ).order_by('-timestamp')[:5]
                    
                    # 添加历史消息（按时间正序）
                    for msg in reversed(history_messages):
                        messages.append({
                            "role": msg.role,
                            "content": msg.content
                        })
                    
                    # 添加当前用户消息
                    messages.append({
                        "role": "user",
                        "content": data.get('message', '')
                    })

                    # 调用OpenAI API
                    api_start = time.time()
                    print(f"\n[6/7] 开始调用OpenAI API: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    response = client.chat.completions.create(
                        model=application.model.name,
                        messages=messages,
                        stream=True,
                        temperature=0.7,  # 使用默认值
                        max_tokens=2000   # 使用默认值
                    )

                    # 记录第一个响应块的时间
                    first_chunk_time = None
                    total_chunks = 0
                    total_content_length = 0
                    full_response = ""
                    full_reasoning = ""

                    # 逐步接收并处理响应
                    print("[yellow]开始接收响应...[/]")
                    for chunk in response:
                        if not chunk.choices:
                            continue
                        
                        # 记录第一个响应块的时间
                        if first_chunk_time is None:
                            first_chunk_time = time.time()
                            print(f"第一个响应块耗时: {first_chunk_time - api_start:.3f}秒")
                        
                        total_chunks += 1
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            total_content_length += len(content)
                            full_response += content
                            # 直接yield数据
                            yield f"data: {json.dumps({'content': content})}\n\n"
                        if chunk.choices[0].delta.reasoning_content:
                            content = chunk.choices[0].delta.reasoning_content
                            total_content_length += len(content)
                            full_reasoning += content
                            yield f"data: {json.dumps({'reasoning_content': content})}\n\n"

                    # 保存助手消息
                    assistant_message = ChatMessage.objects.create(
                        conversation=conversation,
                        role='assistant',
                        content=full_response,
                        reasoning=full_reasoning,
                        tokens=len(full_response) // 4,
                        model_used=application.model
                    )

                    # 更新对话统计
                    conversation.update_stats()

                    # 记录结束时间和统计信息
                    end_time = time.time()
                    print(f"\n[bold green]执行完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]")
                    print(f"[bold cyan]性能统计:[/]")
                    print(f"[dim]总执行时间: {round(end_time - start_time, 3)} 秒[/]")
                    print(f"[dim]API请求总耗时: {round(end_time - api_start, 3)} 秒[/]")
                    print(f"[dim]总响应块数: {total_chunks}[/]")
                    print(f"[dim]总内容长度: {total_content_length} 字符[/]")
                    if total_chunks > 0:
                        print(f"[dim]平均每块耗时: {round((end_time - first_chunk_time) / total_chunks, 3)} 秒[/]")
                        print(f"[dim]平均每字符耗时: {round((end_time - first_chunk_time) / total_content_length, 3)} 秒[/]")

                    yield "data: [DONE]\n\n"

                except Exception as e:
                    print(f"\n流式处理出错: {str(e)}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

            response = StreamingHttpResponse(
                event_stream(),
                content_type='text/event-stream'
            )
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            
            return response

        except Exception as e:
            print(f"\n请求处理错误: {str(e)}")
            return JsonResponse(
                {"error": str(e)},
                status=500
            )

class ChatWidgetView(TemplateView):
    """聊天组件视图"""
    template_name = 'chat/chat_widget.html'
    permission_classes = [AllowAny]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application_id = kwargs.get('application_id')
        
        # 验证应用是否存在
        try:
            application = Application.objects.get(id=application_id, is_active=True)
        except Application.DoesNotExist:
            raise Http404("应用不存在或未激活")
        
        # 获取API URL
        api_url = self.request.GET.get('api_url')
        if not api_url:
            api_url = settings.API_URL if hasattr(settings, 'API_URL') else self.request.build_absolute_uri('/').rstrip('/')
        
        context.update({
            'application_id': application_id,
            'api_url': api_url
        })
        return context

class DesignView(TemplateView):
    """设计页面视图"""
    template_name = 'chat/design.html'
    permission_classes = [AllowAny]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application_id = kwargs.get('application_id')
        
        # 验证应用是否存在
        try:
            application = Application.objects.get(id=application_id, is_active=True)
        except Application.DoesNotExist:
            raise Http404("应用不存在或未激活")
        
        # 获取API URL
        api_url = self.request.GET.get('api_url')
        if not api_url:
            api_url = settings.API_URL if hasattr(settings, 'API_URL') else self.request.build_absolute_uri('/').rstrip('/')
        
        context.update({
            'application_id': application_id,
            'api_url': api_url
        })
        return context