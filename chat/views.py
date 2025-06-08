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
from django.template import Template, Context
import numpy as np
from embeddings.models import Knowledge  # 添加这行导入

User = get_user_model()
logger = logging.getLogger(__name__)




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
                        # 确保系统角色不包含应用名称
                        system_role = application.system_role.replace(application.name, "").strip()
                        if not system_role:
                            system_role = "你是一个智能助手，可以帮助用户解答问题。请保持友好和专业的态度。"
                        messages.append({
                            "role": "system",
                            "content": system_role
                        })
                    
                    # 获取历史消息（只获取用户和助手的消息）
                    history_start = time.time()
                    history_messages = conversation.messages.filter(
                        role__in=['user', 'assistant'],
                        conversation=conversation,  # 确保只获取当前对话的消息
                        id__lt=user_message.id  # 只获取当前消息之前的消息
                    ).order_by('timestamp')  # 按时间正序排列
                    
                    # 添加历史消息
                    for msg in history_messages:
                        messages.append({
                            "role": msg.role,
                            "content": msg.content
                        })
                    
                    # 添加当前用户消息（确保不重复添加）
                    if not messages or messages[-1]['role'] != 'user' or messages[-1]['content'] != data['message']:
                        messages.append({
                            "role": "user",
                            "content": data['message']
                        })
                    
                    print(f"准备历史消息: {time.time() - history_start:.3f}秒")
                    print(f"总消息准备: {time.time() - msg_prep_start:.3f}秒")
                    print(f"历史消息数量: {len(history_messages)}")
                    
                    # 打印完整的消息列表，用于调试
                    print("\n发送给AI的消息列表:")
                    for msg in messages:
                        print(f"{msg['role']}: {msg['content'][:100]}...")
                    
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



class ChatMessageView(APIView):
    """处理聊天消息的视图"""
    permission_classes = [AllowAny]
    
    async def post(self, request, application_id, conversation_id):
        try:
            start_time = time.time()
            print(f"\n{'='*50}")
            print(f"开始执行时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*50}")
            
            # 获取应用实例
            application = Application.objects.get(id=application_id, is_active=True)
                        # 添加日志检查向量模型
            print("\n[bold cyan]应用信息检查:[/]")
            print(f"[dim]应用ID: {application.id}[/]")
            print(f"[dim]应用名称: {application.name}[/]")
            print(f"[dim]向量模型: {application.embedding_model.name if application.embedding_model else '未配置'}[/]")
            if application.embedding_model:
                print(f"[dim]向量模型API: {application.embedding_model.api_url}[/]")
                print(f"[dim]向量模型状态: {'启用' if application.embedding_model.is_active else '禁用'}[/]")
            
            # 获取用户消息
            message = request.data.get('message', '').strip()
            if not message:
                return Response({'error': '消息不能为空'}, status=400)
            
            # 初始化知识库服务
            kb_service = KnowledgeBaseService(application)
            
            # 构建流式响应
            async def generate_response():
                # 如果启用了知识库，先进行语义搜索
                if kb_service.has_knowledge_base():
                    print("\n[yellow]开始处理对话请求...[/]")
                    print("[yellow]开始语义搜索...[/]")
                    
                    # 显示正在处理知识库
                    yield f"data: {json.dumps({'reasoning_content': '开始处理对话请求...\n开始语义搜索...'})}\n\n"
                    
                    # 搜索相关知识
                    search_start = time.time()
                    knowledge_items = await kb_service.search_similar(message)
                    print(f"语义搜索耗时: {round(time.time() - search_start, 3)} 秒")
                    
                    # 显示找到的知识
                    if knowledge_items:
                        print("\n[yellow]找到的相关知识：[/]")
                        for item in knowledge_items:
                            print(f"[dim]相似度: {item[2]:.4f} - {item[1]}[/]")
                        
                        yield f"data: {json.dumps({'reasoning_content': '找到的相关知识：\n' + '\n'.join([f'相似度: {item[2]:.4f} - {item[1]}' for item in knowledge_items])})}\n\n"
                        
                        # 构建带上下文的提示词
                        prompt = kb_service.build_prompt(message, knowledge_items)
                        
                        # 显示发送给AI的完整信息
                        print("\n[yellow]发送给AI的完整信息：[/]")
                        print("[dim]" + "="*50 + "[/]")
                        print("[dim]系统提示：[/]")
                        print("[dim]你是一个智能助手，需要严格基于提供的上下文信息回答问题。如果问题与上下文无关，请明确告知用户。[/]")
                        print("[dim]" + "-"*50 + "[/]")
                        print("[dim]用户提示：[/]")
                        print(f"[dim]{prompt}[/]")
                        print("[dim]" + "="*50 + "[/]")
                        
                        yield f"data: {json.dumps({'reasoning_content': '发送给AI的完整信息：\n' + '='*50 + '\n系统提示：\n你是一个智能助手，需要严格基于提供的上下文信息回答问题。如果问题与上下文无关，请明确告知用户。\n' + '-'*50 + '\n用户提示：\n' + prompt + '\n' + '='*50})}\n\n"
                    else:
                        print("[yellow]未找到相关知识，将直接回答问题...[/]")
                        yield f"data: {json.dumps({'reasoning_content': '未找到相关知识，将直接回答问题...'})}\n\n"
                        prompt = message
                else:
                    prompt = message
                
                # 调用对话模型API
                print("\n[yellow]开始调用对话API...[/]")
                chat_start = time.time()
                
                chat_client = OpenAI(
                    base_url=application.model.api_url,
                    api_key=application.model.api_key
                )
                
                response = chat_client.chat.completions.create(
                    model=application.model.model_name,
                    messages=[
                        {"role": "system", "content": "你是一个智能助手，需要严格基于提供的上下文信息回答问题。如果问题与上下文无关，请明确告知用户。"},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True
                )
                
                # 返回对话结果
                first_chunk_time = None
                total_chunks = 0
                total_content_length = 0
                
                print("\n[yellow]开始接收响应...[/]")
                for chunk in response:
                    if not chunk.choices:
                        continue
                        
                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                        print(f"第一个响应块耗时: {round(first_chunk_time - chat_start, 3)} 秒")
                    
                    total_chunks += 1
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        total_content_length += len(content)
                        yield f"data: {json.dumps({'content': content})}\n\n"
                    if chunk.choices[0].delta.reasoning_content:
                        content = chunk.choices[0].delta.reasoning_content
                        total_content_length += len(content)
                        yield f"data: {json.dumps({'reasoning_content': content})}\n\n"
                
                if total_chunks > 0:
                    print(f"\n[bold cyan]性能统计:[/]")
                    print(f"[dim]总执行时间: {round(time.time() - start_time, 3)} 秒[/]")
                    print(f"[dim]API请求总耗时: {round(time.time() - chat_start, 3)} 秒[/]")
                    print(f"[dim]总响应块数: {total_chunks}[/]")
                    print(f"[dim]总内容长度: {total_content_length} 字符[/]")
                    print(f"[dim]平均每块耗时: {round((time.time() - first_chunk_time) / total_chunks, 3)} 秒[/]")
                    print(f"[dim]平均每字符耗时: {round((time.time() - first_chunk_time) / total_content_length, 3)} 秒[/]")
            
            return StreamingHttpResponse(
                generate_response(),
                content_type='text/event-stream'
            )
            
        except Application.DoesNotExist:
            return Response({'error': '应用不存在或未激活'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

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
            user_message = request.data.get('message')
            
            if not session_id:
                return Response(
                    {"error": "缺少session_id参数"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            application = get_object_or_404(Application, id=application_id, is_active=True)
            
            # 使用用户消息作为标题
            title = user_message[:50] if user_message else '新对话'
            
            conversation = ChatConversation.objects.create(
                application=application,
                session_id=session_id,
                conversation_id=str(uuid.uuid4()),
                title=title,  # 使用用户消息作为标题
                model=application.model
            )
            
            # 不再创建第一条消息，所有消息都通过流式接口插入
            
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
                conversation_id=conversation_id,
                session_id=session_id,
                application=application
            )
            
            # 添加日志检查向量模型
            print("\n[bold cyan]应用信息检查:[/]")
            print(f"[dim]应用ID: {application.id}[/]")
            print(f"[dim]应用名称: {application.name}[/]")
            print(f"[dim]向量模型: {application.embedding_model.name if application.embedding_model else '未配置'}[/]")
            if application.embedding_model:
                print(f"[dim]向量模型API: {application.embedding_model.api_url}[/]")
                print(f"[dim]向量模型状态: {'启用' if application.embedding_model.is_active else '禁用'}[/]")
            
            # 如果启用了向量模型，先获取向量
            if application.embedding_model and application.embedding_model.is_active:
                print("\n[yellow]开始处理对话请求...[/]")
                print("[yellow]开始获取向量...[/]")
                
                try:
                    # 初始化向量模型客户端
                    embedding_client = OpenAI(
                        base_url=application.embedding_model.api_url,
                        api_key=application.embedding_model.api_key
                    )
                    
                    # 获取查询的向量表示
                    embedding_response = embedding_client.embeddings.create(
                        model=application.embedding_model.model_name,
                        input=user_message
                    )
                    
                    query_embedding = embedding_response.data[0].embedding
                    print(f"获取到向量，维度: {len(query_embedding)}")
                    
                    # 从数据库获取知识
                    knowledge_items = application.embedding_model.knowledge_set.filter(
                        is_valid=True
                    )
                    print(f"找到 {knowledge_items.count()} 条知识")
                    
                    # 计算相似度并排序
                    results = []
                    for item in knowledge_items:
                        try:
                            # 获取知识文本的向量表示
                            item_embedding_response = embedding_client.embeddings.create(
                                model=application.embedding_model.model_name,
                                input=item.question  # 使用问题作为向量生成的输入
                            )
                            item_embedding = item_embedding_response.data[0].embedding
                            
                            # 计算余弦相似度
                            dot_product = np.dot(query_embedding, item_embedding)
                            norm_query = np.linalg.norm(query_embedding)
                            norm_vec = np.linalg.norm(item_embedding)
                            
                            if norm_query == 0 or norm_vec == 0:
                                print(f"知识项 {item.id} 的向量范数为0")
                                continue
                                
                            similarity = dot_product / (norm_query * norm_vec)
                            print(f"知识项 {item.id} 相似度: {similarity:.4f}")
                            
                            # 添加相似度阈值判断的日志
                            print(f"当前相似度阈值: {application.knowledge_similarity_threshold}")
                            if similarity >= application.knowledge_similarity_threshold:
                                print(f"知识项 {item.id} 相似度 {similarity:.4f} 超过阈值 {application.knowledge_similarity_threshold}，将被使用")
                                results.append((item.id, item.answer, similarity))  # 使用答案作为上下文
                            else:
                                print(f"知识项 {item.id} 相似度 {similarity:.4f} 未达到阈值 {application.knowledge_similarity_threshold}，将被忽略")
                        except Exception as e:
                            print(f"处理知识项 {item.id} 时出错: {str(e)}")
                            continue
                    
                    # 按相似度排序并获取前N个结果
                    results.sort(key=lambda x: x[2], reverse=True)
                    results = results[:application.max_knowledge_items]
                    
                    if results:
                        print("\n[yellow]找到的相关知识：[/]")
                        for item in results:
                            print(f"[dim]相似度: {item[2]:.4f} - {item[1]}[/]")
                        
                        # 构建带上下文的提示词
                        context = "\n".join([f"- {item[1]}" for item in results])
                        prompt = f"""基于以下上下文信息回答问题：

上下文信息：
{context}

用户问题：{user_message}

请基于上述上下文信息回答问题。如果问题与上下文无关，请明确告知用户。"""
                    else:
                        print("[yellow]未找到相关知识，将直接回答问题...[/]")
                        prompt = user_message
                except Exception as e:
                    print(f"处理向量时出错: {str(e)}")
                    prompt = user_message
            else:
                prompt = user_message
            
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
                        print(f"使用系统角色: {application.system_role}")
                        # 确保系统角色不包含应用名称
                        system_role = application.system_role.replace(application.name, "").strip()
                        if not system_role:
                            system_role = "你是一个智能助手，可以帮助用户解答问题。请保持友好和专业的态度。"
                        messages.append({
                            "role": "system",
                            "content": system_role
                        })
                    
                    # 获取历史消息（只获取用户和助手的消息）
                    history_start = time.time()
                    history_messages = conversation.messages.filter(
                        role__in=['user', 'assistant'],
                        conversation=conversation,  # 确保只获取当前对话的消息
                        id__lt=user_message_obj.id  # 只获取当前消息之前的消息
                    ).order_by('timestamp')  # 按时间正序排列
                    
                    # 添加历史消息
                    for msg in history_messages:
                        messages.append({
                            "role": msg.role,
                            "content": msg.content
                        })
                    
                    # 添加当前用户消息（确保不重复添加）
                    if not messages or messages[-1]['role'] != 'user' or messages[-1]['content'] != user_message:
                        messages.append({
                            "role": "user",
                            "content": prompt  # 使用处理后的prompt
                        })

                    # 打印完整的消息列表，用于调试
                    print("\n发送给AI的消息列表:")
                    for msg in messages:
                        print(f"{msg['role']}: {msg['content'][:100]}...")

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
