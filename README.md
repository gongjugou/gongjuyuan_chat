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
- git clone https://gitee.com/xujiusi/gongjuyuan_chat.git

### 2.修改设置文件配置域名
修改：gongjuyuan_chat-gongjuyuan_chat-settings.py
下面三处，域名改成自己的。

ALLOWED_HOSTS = ['chat.gongjuyuan.com']

CSRF_TRUSTED_ORIGINS = [
    'https://chat.gongjuyuan.com',
]

ALLOWED_HOSTS = [
    'chat.gongjuyuan.com',  # 主API域名
]

### 3. 运行
```bash
# 进入 Dockerfile 所在目录
cd gongjuyuan_chat

# 构建镜像
docker-compose up -d
```

### 3.查看

访问 http://域名/api/chat/ui/2/
右下角，会出现聊天按钮，不能对话，因为得到后台添加自己的api

>>>>>>> d2dbacef37002d9c43e68b7031d1d3e64cbe4ebc

## 后台管理

### 登录信息
- 域名/admin
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