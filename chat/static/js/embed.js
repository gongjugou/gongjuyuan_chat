(function() {
    // 创建配置对象
    const config = {
        protocol: 'http',
        host: '127.0.0.1:7000',
        token: 'your-token-here'  // 这里需要替换为实际的token
    };

    // 创建样式
    const style = document.createElement('style');
    style.textContent = `
        .chat-widget {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 999999;
        }

        .chat-widget .chat-container {
            position: fixed;
            bottom: 90px;
            right: 20px;
            width: 360px;
            height: 500px;
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            display: none;
            flex-direction: column;
            overflow: hidden;
            transition: all 0.3s ease;
        }

        .chat-widget .chat-container.expanded {
            width: 50vw;
            height: 100vh;
            bottom: 0;
            right: 0;
            border-radius: 0;
        }

        @media (max-width: 768px) {
            .chat-widget .chat-container {
                width: 100%;
                height: 100%;
                bottom: 0;
                right: 0;
                border-radius: 0;
            }
        }
    `;
    document.head.appendChild(style);

    // 创建容器
    const container = document.createElement('div');
    container.className = 'chat-widget';
    document.body.appendChild(container);

    // 加载聊天组件
    fetch(`${config.protocol}://${config.host}/api/chat/design/`)
        .then(response => response.text())
        .then(html => {
            container.innerHTML = html;
            
            // 重新绑定事件
            const robotAvatar = container.querySelector('.robot-avatar');
            const chatContainer = container.querySelector('.chat-container');
            const closeBtn = container.querySelector('.chat-header-btn[title="关闭"]');
            const expandBtn = container.querySelector('.chat-header-btn[title="放大"]');
            const historyBtn = container.querySelector('#historyBtn');
            const historyList = container.querySelector('#historyList');

            // 机器人头像点击事件
            robotAvatar.onclick = function() {
                chatContainer.style.display = 'flex';
                robotAvatar.style.display = 'none';
            };

            // 关闭按钮事件
            closeBtn.onclick = function() {
                chatContainer.style.display = 'none';
                robotAvatar.style.display = 'flex';
            };

            // 展开/收起事件
            expandBtn.onclick = function() {
                chatContainer.classList.toggle('expanded');
                this.querySelector('i').className = chatContainer.classList.contains('expanded') 
                    ? 'ri-fullscreen-exit-line' 
                    : 'ri-fullscreen-line';
                this.title = chatContainer.classList.contains('expanded') ? '收起' : '放大';
            };

            // 历史记录按钮事件
            historyBtn.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                historyList.classList.toggle('show');
            };

            // 点击其他地方关闭历史记录
            document.addEventListener('click', function(e) {
                if (!historyList.contains(e.target) && !historyBtn.contains(e.target)) {
                    historyList.classList.remove('show');
                }
            });

            // 阻止历史记录列表的点击事件冒泡
            historyList.addEventListener('click', function(e) {
                e.stopPropagation();
            });
        })
        .catch(error => {
            console.error('加载聊天组件失败:', error);
        });
})(); 