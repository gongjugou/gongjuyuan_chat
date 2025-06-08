import requests
import numpy as np
from .models import EmbeddingModel, Knowledge, APICallLog
from datetime import datetime
import time

class EmbeddingService:
    def __init__(self, model: EmbeddingModel):
        self.model = model
        self.api_url = model.api_url
        self.api_key = model.api_key
        self.model_name = model.model_name
        self.dimension = model.dimension

    def get_embedding(self, text: str) -> np.ndarray:
        """获取文本的向量表示"""
        start_time = time.time()
        
        # 准备API请求
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "input": text,
            "encoding_format": "float"
        }
        
        # 调用API
        response = requests.post(self.api_url, json=payload, headers=headers)
        
        # 记录API调用
        APICallLog.objects.create(
            model=self.model,
            api_type='embedding',
            request_data=payload,
            response_data=response.json() if response.status_code == 200 else {"error": response.text},
            status_code=response.status_code,
            duration=time.time() - start_time
        )
        
        if response.status_code != 200:
            raise Exception(f"Embedding API调用失败: {response.text}")
            
        # 获取向量并转换为numpy数组
        embedding = response.json()["data"][0]["embedding"]
        embedding_array = np.array(embedding, dtype=np.float32)
        
        # 验证向量维度
        if embedding_array.shape[0] != self.dimension:
            raise Exception(f"向量维度不匹配 - 期望: {self.dimension}, 实际: {embedding_array.shape[0]}")
            
        return embedding_array

    def calculate_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算两个向量的余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)

    def search_similar(self, query: str, top_k: int = 3) -> list:
        """搜索相似知识"""
        # 获取查询文本的向量表示
        query_embedding = self.get_embedding(query)
        
        # 获取所有知识
        all_knowledge = Knowledge.objects.filter(
            model=self.model,
            is_valid=True
        )
        
        # 计算相似度并排序
        results = []
        for knowledge in all_knowledge:
            knowledge_embedding = knowledge.get_embedding_array()
            similarity = self.calculate_similarity(query_embedding, knowledge_embedding)
            results.append((knowledge, similarity))
        
        # 按相似度排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k] 