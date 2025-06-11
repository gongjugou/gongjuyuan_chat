from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = 'django-insecure-a(dlxgxnxt@cmg17oepuj0@qe&os3)d%s4$a39-6^^-#juvh%x'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False  # 开发环境设置为True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'chat.gongjuyuan.com', '	10.62.169.173']

LOGIN_URL = '/admin/login/'  # 使用Django admin的登录页面
LOGIN_REDIRECT_URL = '/admin/'  # 登录后重定向到admin界面

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework', # 添加rest_framework
    # 'rest_framework.authtoken', # 添加rest_framework.authtoken
    'chat', # 添加chat
    'corsheaders',  # cors配置app
    'embeddings', # 添加embeddings
]


# 在文件末尾添加以下 DRF 配置
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],  # 移除所有认证类
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # 允许任何人访问
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}


# 禁用Django的CORS中间件
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # cors配置
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# 允许所有配置。
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

ROOT_URLCONF = 'gongjuyuan_chat.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'gongjuyuan_chat.wsgi.application'



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# 将语言改为简体中文
LANGUAGE_CODE = 'zh-hans'  # 原为 'en-us'

# 将时区改为中国时区
TIME_ZONE = 'Asia/Shanghai'  # 原为 'UTC'

USE_I18N = True

USE_TZ = True



STATIC_URL = '/static/'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# API配置
API_URL = 'http://127.0.0.1:9000'  # 开发环境
# API_URL = 'https://您的域名'  # 生产环境



# 静态文件设置
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # 用于收集静态文件
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),  # 你的静态文件目录
]
