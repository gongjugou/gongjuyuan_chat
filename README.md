
### 在线体验--复制代码放到首页就可以看见右下角的对话客服了.
> 注意：由于服务器位于家庭环境，可能无法保证 24 小时在线
想测试速度可以访问：www.gongjuyuan.com  服务器在家，有可能访问不通，
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

# 工具猿聊天机器人部署指南

## 部署步骤

### 1. 服务器准备
- SSH 登录服务器
- 通过 git 克隆或下载 zip 包并解压到服务器

### 2. 域名配置
进入 `gongjuyuan_chat` 目录，修改 `settings.py` 中的 `ALLOWED_HOSTS` 配置：
- 添加您的域名（必填）
- 添加公网 IP（必填）

### 3. 启动服务
```bash
# 进入项目目录
cd gongjuyuan_chat

# 启动 Docker 容器
docker-compose up -d
```

### 4. 容器说明
系统会创建两个容器：
- Nginx 服务（端口：9000）
- Django 服务（内部端口，不对外暴露）

### 5. 宝塔配置
1. 创建新网站
2. 域名需与 `settings.py` 中配置的域名一致
3. 设置反向代理：`http://公网ip:9000`
4. 反向代理配置文件中： proxy_set_header 这行改成：proxy_set_header Host $host; 


### 6. 题外话：
如果你本地测试，部署完，访问 `127.0.0.1:9000/admin` 能看见内容，就算成功，因为django不代理静态了，
> 注意：如果静态文件（如 CSS）显示异常，这是正常的，因为 Django 的 debug 模式关闭后，静态文件将由 Nginx 代理

## 后台配置

### 登录信息
- 用户名：`admin`
- 密码：`gongjuyuan`

### 必要配置
1. 进入模型设置，配置您的 API 密钥
2. 进入向量模型设置，配置您的 API 密钥

### 知识库管理
为应用选择向量模型后，可以添加自定义知识，例如：
- 问：牙合是什么公司？
- 答：牙合是一个位于中国深圳的AI公司，专注于AI技术的研发和应用。

## 网站集成

### 安装代码
```html
<!-- 1. 配置 -->
<script>
  window.ChatWidget = {
      config: {
          application_id: 2,  // 您的应用ID
          protocol: 'http',   // 协议
          host: '127.0.0.1:8000'  // 主机地址
      }
  };
</script>

<!-- 2. 加载脚本 -->
<script async defer src="http://127.0.0.1:8000/static/js/ui-embed.js"></script>
```

#### 目前只支持硅基流动的api，用的人多了，再考虑...

## Docker 管理

### 清理命令
```bash
# 删除所有容器、镜像和卷
docker-compose down --rmi all --volumes --remove-orphans
```
