使用方法
部署：
1：ssh登录服务器：git下载到服务器 ，或者下载zip包，上传到服务器后解压
2：绑定域名或者公网ip：需要进入gongjuyuan_chat目录下找到settings.py   修改ALLOWED_HOSTS配置，绑定自己的域名（必填）和公网ip（必填）（涉及到后面绑定域名使用）
3：ssh进入目录， docker-compose up -d
4：会创建两个容器，一个服务是nginx，端口使用了9000，一个是django，未暴漏端口
5：宝塔：建立一个网站，域名需要和settings.py 里面的域名一样，然后设置，反向代理，http://公网ip:9000

6:本地如果测试使用，需要在settings.py 添加本机ip127.0.0.1:9000/admin 测试一下，

# 安装到任何网站：
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


# 体验：注意，我没有全体24小时开放，因为我的服务器在家里，没开启，就显示不出来，
    <!-- 1. 配置 -->
<script>
  window.ChatWidget = {
      config: {
          application_id: 2,  // 您的应用ID
          protocol: 'http',   // 协议
          host: 'chat.gongjuyuan.com'  // 主机地址
      }
  };
</script>

<!-- 2. 加载脚本 -->
<script async defer src="http://chat.gongjuyuan.com/static/js/ui-embed.js"></script>













1：django默认开启了cors全部允许.
nginx配置，参考使用nginx.conf的即可，
解释：配置一下静态，配置一下媒体，配置一下代理 即可。


2：如果需要配置cors，
nginx配置，参考用nginx.conf2 即可
解释：
2.1：添加CORS相关配置允许域名访问，
2.2：静态添加CORS头，
2.3：媒体添加CORS头，
2.4：代理添加CORS头
2.5：删掉配置文件内的以下代码：
'''
INSTALLED_APPS = [
    ...
    'corsheaders',
    ...
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # 必须放在最前面
    ...
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
'''

