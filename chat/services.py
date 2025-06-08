from embeddings.services import EmbeddingService
from embeddings.models import Knowledge
from typing import List, Tuple
import numpy as np

class KnowledgeService:
    def __init__(self, application):
        self.application = application
        self.embedding_model = application.embedding_model
        self.similarity_threshold = application.knowledge_similarity_threshold
        self.max_items = application.max_knowledge_items
        
    def search_knowledge(self, query: str) -> List[Tuple[Knowledge, float]]:
        """搜索相关知识"""
        if not self.embedding_model:
            return []
            
        # 创建向量服务
        service = EmbeddingService(self.embedding_model)
        
        # 搜索相似知识
        results = service.search_similar(query, top_k=self.max_items)
        
        # 过滤相似度低于阈值的结果
        filtered_results = [
            (knowledge, similarity) 
            for knowledge, similarity in results 
            if similarity >= self.similarity_threshold
        ]
        
        return filtered_results
        
    def format_knowledge_context(self, query: str) -> str:
        """格式化知识上下文"""
        results = self.search_knowledge(query)
        if not results:
            return ""
            
        context = "以下是相关的知识信息：\n\n"
        for knowledge, similarity in results:
            context += f"[相似度: {similarity:.2f}] {knowledge.text}\n\n"
            
        return context.strip() 