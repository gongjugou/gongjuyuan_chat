from django.db import models
from django.utils import timezone
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import json
import requests
import time

class EmbeddingModel(models.Model):
    """向量模型配置"""
    name = models.CharField('模型名称', max_length=100)
    model_name = models.CharField('模型标识', max_length=100)
    description = models.TextField('描述', blank=True)
    api_url = models.URLField('API地址')
    api_key = models.CharField('API密钥', max_length=200, blank=True)
    dimension = models.IntegerField('向量维度', default=1024)
    encoding_format = models.CharField('编码格式', max_length=50, default='float')
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '向量模型'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class Knowledge(models.Model):
    """知识库"""
    question = models.CharField('问题', max_length=500)
    answer = models.TextField('答案')
    model = models.ForeignKey(EmbeddingModel, on_delete=models.CASCADE, verbose_name='向量模型')
    is_valid = models.BooleanField('是否有效', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '知识'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model', 'is_valid']),
            models.Index(fields=['question']),
        ]

    def __str__(self):
        return self.question



