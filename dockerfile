FROM python:3.9 as builder

# 设置工作目录（改为项目相关名称）
WORKDIR /gongjuyuan_chat


COPY . /gongjuyuan_chat/


# 安装依赖（使用清华镜像加速）
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install --no-cache-dir uwsgi \
    -i https://pypi.tuna.tsinghua.edu.cn/simple



ENV PYTHONPATH=/gongjuyuan_chat



# 设置入口点（确保路径正确）
ENTRYPOINT ["python", "/gongjuyuan_chat/entrypoint.py"]