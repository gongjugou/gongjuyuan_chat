from django.db import models
import numpy as np
import requests
import time

class EmbeddingModel(models.Model):
    """向量模型"""
    name = models.CharField(max_length=100, verbose_name="模型名称")
    model_name = models.CharField(max_length=100, verbose_name="模型标识")
    description = models.TextField(verbose_name="模型描述", blank=True)
    api_url = models.URLField(verbose_name="API地址")
    api_key = models.CharField(max_length=100, verbose_name="API密钥")
    dimension = models.IntegerField(verbose_name="向量维度")
    encoding_format = models.CharField(
        max_length=20,
        default="float",
        verbose_name="编码格式"
    )
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "向量模型"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.model_name})"

    def get_embedding(self, text: str) -> np.ndarray:
        """获取文本的向量表示"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model_name,
                "input": text,
                "encoding_format": self.encoding_format
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers
            )
            
            if response.status_code != 200:
                raise Exception(f"Embedding API 调用失败: {response.text}")
                
            embedding = response.json()["data"][0]["embedding"]
            return np.array(embedding, dtype=np.float32)
            
        except Exception as e:
            raise Exception(f"获取向量表示失败: {str(e)}")

    def add_knowledge(self, text: str) -> 'Knowledge':
        """添加知识到知识库"""
        from .models import Knowledge  # 在方法内部导入，避免循环引用
        
        try:
            print(f"[yellow]开始添加知识: {text[:50]}...[/]")
            
            # 获取文本的向量表示
            embedding_start = time.time()
            embedding = self.get_embedding(text)
            print(f"Embedding API调用耗时: {round(time.time() - embedding_start, 3)} 秒")
            
            if embedding is None:
                raise Exception("获取向量表示失败")
                
            # 验证向量维度
            if embedding.shape[0] != self.dimension:
                raise Exception(f"向量维度不匹配 - 期望: {self.dimension}, 实际: {embedding.shape[0]}")
            
            # 创建知识记录
            db_start = time.time()
            knowledge = Knowledge.objects.create(
                text=text,
                model=self
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

class Knowledge(models.Model):
    """知识库"""
    text = models.TextField(verbose_name="知识内容")
    embedding = models.BinaryField(verbose_name="向量嵌入")
    model = models.ForeignKey(
        EmbeddingModel, 
        on_delete=models.CASCADE, 
        verbose_name="使用的模型"
    )
    similarity_score = models.FloatField(
        default=0.0,
        verbose_name="相似度分数"
    )
    is_valid = models.BooleanField(
        default=True,
        verbose_name="是否有效"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "知识库"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def get_embedding_array(self):
        """将二进制向量转换为numpy数组"""
        try:
            if not self.embedding:
                print(f"知识项 {self.id} 的向量为空")
                return None
                
            array = np.frombuffer(self.embedding, dtype=np.float32)
            if len(array) == 0:
                print(f"知识项 {self.id} 的向量长度为0")
                return None
                
            return array
        except Exception as e:
            print(f"获取知识项 {self.id} 的向量时出错: {str(e)}")
            return None

    def set_embedding_array(self, array):
        """将numpy数组转换为二进制存储"""
        try:
            if array is None or len(array) == 0:
                print(f"知识项 {self.id} 的输入向量为空")
                return
                
            if not isinstance(array, np.ndarray):
                array = np.array(array, dtype=np.float32)
                
            self.embedding = array.tobytes()
        except Exception as e:
            print(f"设置知识项 {self.id} 的向量时出错: {str(e)}")

class APICallLog(models.Model):
    """API调用日志"""
    model = models.ForeignKey(
        EmbeddingModel,
        on_delete=models.CASCADE,
        verbose_name="使用的模型"
    )
    api_type = models.CharField(
        max_length=20,
        choices=[
            ('EMBEDDING', '向量生成'),
            ('CHAT', '对话生成')
        ],
        verbose_name="API类型"
    )
    request_data = models.JSONField(verbose_name="请求数据")
    response_data = models.JSONField(verbose_name="响应数据")
    status_code = models.IntegerField(verbose_name="状态码")
    duration = models.FloatField(verbose_name="耗时(秒)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "API调用日志"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']