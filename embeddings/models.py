from django.db import models
import numpy as np

class EmbeddingModel(models.Model):
    """向量模型配置"""
    name = models.CharField(max_length=100, verbose_name="模型名称")
    api_url = models.URLField(verbose_name="API地址")
    api_key = models.CharField(max_length=255, verbose_name="API密钥")
    model_name = models.CharField(max_length=100, verbose_name="模型标识")
    dimension = models.IntegerField(verbose_name="向量维度")
    description = models.TextField(verbose_name="模型描述", blank=True)
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    encoding_format = models.CharField(
        max_length=50, 
        default="float",
        verbose_name="编码格式"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "向量模型"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name

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
        max_length=50,
        choices=[
            ('embedding', '向量化'),
            ('chat', '对话')
        ],
        verbose_name="API类型"
    )
    request_data = models.JSONField(verbose_name="请求数据")
    response_data = models.JSONField(verbose_name="响应数据")
    status_code = models.IntegerField(verbose_name="状态码")
    duration = models.FloatField(verbose_name="耗时(秒)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="调用时间")

    class Meta:
        verbose_name = "API调用日志"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']