使用方法
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

