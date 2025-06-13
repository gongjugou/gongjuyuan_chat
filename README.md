# 工具猿聊天机器人部署指南

## 快速体验
> 注意：由于服务器位于家庭环境，可能无法保证 24 小时在线
> 测试地址：www.gongjuyuan.com（服务器在家，可能无法访问）

将以下代码复制到您的网站首页，即可在右下角看到对话客服：

```html
<!-- 1. 配置 -->
<script>
  window.ChatWidget = {
      config: {
          application_id: 2,  // 您的应用ID
          protocol: 'https',   // 协议
          host: 'chat.gongjuyuan.com'  // 主机地址
      }
  };
</script>

<!-- 2. 加载脚本 -->
<script async defer src="https://chat.gongjuyuan.com/static/js/ui-embed.js"></script>
```

## 服务器部署指南

### 1. 环境准备
- SSH 登录服务器
- 通过 git 克隆或下载 zip 包并解压到服务器

### 2. 域名配置
进入 `gongjuyuan_chat` 目录，修改 `settings.py` 中的 `ALLOWED_HOSTS` 配置：
- 添加您的域名（必填，用于 Nginx 反向代理）
- 添加服务器公网 IP（选填，如果计划使用 IP 访问）

### 3. 构建镜像
```bash
# 进入 Dockerfile 所在目录
cd /path/to/dockerfile

# 构建镜像
docker build -t gongjuyuan-chat:latest .
```

### 4. 运行容器
```bash
# 创建数据目录
sudo mkdir -p /data/gongjuyuan_chat/static /data/gongjuyuan_chat/media
sudo chmod -R 755 /data/gongjuyuan_chat

# 启动容器
docker run -d --name chat-app \
  -p 127.0.0.1:8000:8000 \
  --restart unless-stopped \
  -v /data/gongjuyuan_chat/static:/gongjuyuan_chat/staticfiles \
  -v /data/gongjuyuan_chat/media:/gongjuyuan_chat/media \
  gongjuyuan-chat:latest
```

### 5. Nginx 配置（宝塔面板）

#### 5.1 创建网站
1. 新建网站，绑定域名或 IP
2. 设置反向代理：
   - 代理名称：chat
   - 目标 URL：http://127.0.0.1:8000

#### 5.2 反向代理配置
```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

#### 5.3 静态文件配置
```nginx
# 静态文件
location /static/ {
    alias /gongjuyuan_chat/staticfiles/;
    expires 30d;
    access_log off;
}

# 媒体文件
location /media/ {
    alias /gongjuyuan_chat/media/;
    expires 30d;
    access_log off;
}
```

## 后台管理

### 登录信息
- 用户名：`admin`
- 密码：`gongjuyuan`

### 必要配置
1. 进入模型设置，配置 API 密钥
2. 进入向量模型设置，配置 API 密钥

### 知识库管理
为应用选择向量模型后，可以添加自定义知识，例如：
- 问：牙合是什么公司？
- 答：牙合是一个位于中国深圳的AI公司，专注于AI技术的研发和应用。

## 网站集成

### 安装代码
> 注意：请先申请 SSL 证书（推荐使用免费的 Let's Encrypt）

```html
<!-- 1. 配置 -->
<script>
  window.ChatWidget = {
      config: {
          application_id: 2,  // 您的应用ID
          protocol: 'https',   // 协议
          host: '您的域名'  // 主机地址
      }
  };
</script>

<!-- 2. 加载脚本 -->
<script async defer src="https://您的域名/static/js/ui-embed.js"></script>
```

> 目前仅支持硅基流动的 API，后续会考虑支持更多模型

## 维护管理

### 容器管理
```bash
# 查看容器状态
docker ps -a

# 查看容器日志
docker logs chat-app

# 重启容器
docker restart chat-app

# 停止容器
docker stop chat-app

# 删除容器
docker rm chat-app
```

### 数据备份
- 静态文件位置：`/data/gongjuyuan_chat/static`
- 媒体文件位置：`/data/gongjuyuan_chat/media`
- 建议定期备份这些目录
