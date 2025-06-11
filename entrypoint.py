import os
import sys
import logging
import subprocess
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_migrations():
    try:
        # 确保静态文件和媒体目录存在
        Path('/gongjuyuan_chat/staticfiles').mkdir(parents=True, exist_ok=True)
        Path('/gongjuyuan_chat/media').mkdir(parents=True, exist_ok=True)

        # 运行数据库迁移
        logger.info("Running database migrations...")
        subprocess.run(['python', 'manage.py', 'migrate'], check=True)
        
        # 收集静态文件
        logger.info("Collecting static files...")
        subprocess.run(['python', 'manage.py', 'collectstatic', '--noinput'], check=True)
        
        logger.info("Migrations and static files collection completed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error during migrations: {e}")
        sys.exit(1)

def main():
    # 设置 Django 环境变量（确保与项目名一致）
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gongjuyuan_chat.settings')
    
    # 运行迁移
    run_migrations()

    # 启动 uWSGI
    uwsgi_args = [
        '/usr/local/bin/uwsgi',
        '--socket', '0.0.0.0:8000',
        '--protocol', 'uwsgi',
        '--chdir', '/gongjuyuan_chat',  # 改为项目目录
        '--module', 'gongjuyuan_chat.wsgi:application',  # 适配项目名
        '--processes', '4',
        '--threads', '2',
        '--harakiri', '30',
        '--max-requests', '500',
        '--disable-logging',
        '--thunder-lock',
        '--enable-threads',
        '--master',
        '--pidfile', '/tmp/project-master.pid',
        '--vacuum',
        '--buffer-size', '32768'
    ]

    try:
        logger.info("Starting uwsgi server...")
        os.execvp('/usr/local/bin/uwsgi', uwsgi_args)
    except Exception as e:
        logger.error(f"Failed to start uwsgi: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()