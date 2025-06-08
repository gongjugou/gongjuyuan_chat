from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .models import EmbeddingModel, Knowledge
from .services import EmbeddingService
from django.shortcuts import get_object_or_404

# Create your views here.

class KnowledgeSearchView(APIView):
    """知识库搜索视图"""
    permission_classes = [AllowAny]
    
    def post(self, request, model_id):
        try:
            # 获取查询参数
            query = request.data.get('query')
            top_k = request.data.get('top_k', 3)
            
            if not query:
                return Response(
                    {"error": "请提供查询文本"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 获取向量模型
            model = get_object_or_404(EmbeddingModel, id=model_id, is_active=True)
            
            # 创建向量服务
            service = EmbeddingService(model)
            
            # 搜索相似知识
            results = service.search_similar(query, top_k=top_k)
            
            # 格式化结果
            formatted_results = []
            for knowledge, similarity in results:
                formatted_results.append({
                    'id': knowledge.id,
                    'text': knowledge.text,
                    'similarity': float(similarity),
                    'created_at': knowledge.created_at
                })
            
            return Response({
                'query': query,
                'results': formatted_results
            })
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
