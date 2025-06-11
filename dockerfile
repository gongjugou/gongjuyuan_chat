FROM python:3.9 as builder

# 设置工作目录（改为项目相关名称）
WORKDIR /gongjuyuan_chat_build

# 首先只复制依赖文件，利用缓存
COPY requirements.txt .

# 安装依赖（使用清华镜像加速）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir uwsgi

# 最终阶段
FROM python:3.9

# 设置工作目录（改为项目名称）
WORKDIR /gongjuyuan_chat

# 从构建阶段复制Python包和uWSGI
COPY --from=builder /usr/local/lib/python3.9/site-packages/ /usr/local/lib/python3.9/site-packages/
COPY --from=builder /usr/local/bin/uwsgi /usr/local/bin/uwsgi

# 复制项目文件
COPY . /gongjuyuan_chat/

# 设置环境变量（同步项目名称）
ENV PYTHONPATH=/gongjuyuan_chat \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=gongjuyuan_chat.settings

# 创建非root用户
RUN useradd -m -u 1000 appuser \
    && mkdir -p /gongjuyuan_chat/staticfiles /gongjuyuan_chat/media /gongjuyuan_chat/db \
    && chown -R appuser:appuser /gongjuyuan_chat \
    && chmod -R 777 /gongjuyuan_chat/staticfiles /gongjuyuan_chat/media /gongjuyuan_chat/db

# 切换到非root用户
USER appuser

# 设置入口点（确保路径正确）
ENTRYPOINT ["python", "/gongjuyuan_chat/entrypoint.py"]