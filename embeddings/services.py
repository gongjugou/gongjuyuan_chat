# embeddings/services.py

import requests
import numpy as np
from django.conf import settings
from .models import EmbeddingModel, Knowledge
import time

class EmbeddingService:
    """向量模型服务"""
    
    def __init__(self, model: EmbeddingModel):
        self.model = model
        
    def get_embedding(self, text: str) -> np.ndarray:
        """获取文本的向量表示"""
        try:
            headers = {
                "Authorization": f"Bearer {self.model.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model.model_name,
                "input": text,
                "encoding_format": self.model.encoding_format
            }
            
            response = requests.post(
                self.model.api_url,
                json=payload,
                headers=headers
            )
            
            if response.status_code != 200:
                raise Exception(f"Embedding API 调用失败: {response.text}")
                
            embedding = response.json()["data"][0]["embedding"]
            return np.array(embedding, dtype=np.float32)
            
        except Exception as e:
            raise Exception(f"获取向量表示失败: {str(e)}")
    
    def add_knowledge(self, text: str) -> Knowledge:
        """添加知识到知识库"""
        try:
            print(f"[yellow]开始添加知识: {text[:50]}...[/]")
            
            # 获取文本的向量表示
            embedding_start = time.time()
            embedding = self.get_embedding(text)
            print(f"Embedding API调用耗时: {round(time.time() - embedding_start, 3)} 秒")
            
            if embedding is None:
                raise Exception("获取向量表示失败")
                
            # 验证向量维度
            if embedding.shape[0] != 1024:  # BAAI/bge-large-zh-v1.5 的维度
                raise Exception(f"向量维度不匹配 - 期望: 1024, 实际: {embedding.shape[0]}")
            
            # 创建知识记录
            db_start = time.time()
            knowledge = Knowledge.objects.create(
                text=text,
                model=self.model
            )
            
            # 设置向量
            knowledge.set_embedding_array(embedding)
            knowledge.save()
            print(f"数据库存储耗时: {round(time.time() - db_start, 3)} 秒")
            print(f"[green]成功添加知识，ID: {knowledge.id}[/]")
            
            return knowledge
            
        except Exception as e:
            print(f"[red]添加知识失败: {str(e)}[/]")
            raise
    
    def search_similar(self, query: str, top_k: int = 3, threshold: float = 0.7) -> list:
        """搜索相似知识"""
        try:
            # 获取查询文本的向量表示
            query_embedding = self.get_embedding(query)
            
            # 从数据库读取所有知识
            results = []
            for item in Knowledge.objects.filter(model=self.model, is_valid=True):
                try:
                    vec = item.get_embedding_array()
                    
                    # 计算余弦相似度
                    dot_product = np.dot(query_embedding, vec)
                    norm_query = np.linalg.norm(query_embedding)
                    norm_vec = np.linalg.norm(vec)
                    
                    if norm_query == 0 or norm_vec == 0:
                        similarity = 0.0
                    else:
                        similarity = dot_product / (norm_query * norm_vec)
                    
                    if similarity >= threshold:
                        results.append((item, similarity))
                except Exception as e:
                    print(f"警告：处理向量时出错 - {str(e)}")
                    continue
            
            # 按相似度排序
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            raise Exception(f"搜索相似知识失败: {str(e)}")