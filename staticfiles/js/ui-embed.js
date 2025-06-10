(function() {
    console.log('=== 聊天组件初始化开始 ===');
    
    // 创建配置对象
    const config = {
        protocol: window.location.protocol.replace(':', ''),
        host: window.location.host,
        application_id: 1,
        token: 'your-token-here'
    };
    console.log('初始配置:', config);

    // 如果存在全局配置，则合并
    if (window.ChatWidget && window.ChatWidget.config) {
        console.log('发现全局配置:', window.ChatWidget.config);
        // 确保用户配置优先
        config.application_id = window.ChatWidget.config.application_id || config.application_id;
        config.protocol = window.ChatWidget.config.protocol || config.protocol;
        config.host = window.ChatWidget.config.host || config.host;
        config.token = window.ChatWidget.config.token || config.token;
        console.log('合并后的配置:', config);
    }

    // 检查是否提供了应用ID
    if (!config.application_id) {
        console.error('错误: 请提供应用ID (application_id)');
        return;
    }

    // 构建基础URL
    const baseUrl = `${config.protocol}://${config.host}`;
    // 构建静态文件基础URL
    const staticBaseUrl = `${baseUrl}/static`;
    console.log('基础URL:', baseUrl);
    console.log('静态文件基础URL:', staticBaseUrl);

    // 构建聊天组件URL
    const chatUrl = `${baseUrl}/api/chat/ui/${config.application_id}/`;
    console.log('聊天组件URL:', chatUrl);

    // 创建样式
    console.log('开始创建样式...');
    const style = document.createElement('style');
    style.textContent = `
        .chat-widget {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 999999;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }

        .chat-widget .robot-avatar {
            width: 60px;
            height: 60px;
            background: transparent;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: none;
            overflow: hidden;
        }

        .chat-widget .robot-avatar:hover {
            transform: translateY(-5px);
        }

        .chat-widget .robot-avatar img {
            width: 100%;
            height: 100%;
            object-fit: contain;
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
            border: 1px solid #e5e7eb;
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
    console.log('样式创建完成');

    // 创建容器
    console.log('开始创建容器...');
    const container = document.createElement('div');
    container.className = 'chat-widget';
    container.innerHTML = `
        <div class="robot-avatar">
            <img src="${staticBaseUrl}/images/logo.svg" alt="智能客服">
        </div>
        <div class="chat-container"></div>
    `;
    document.body.appendChild(container);
    console.log('容器创建完成，DOM结构:', container.outerHTML);

    // 直接绑定机器人头像点击事件
    const robotAvatar = container.querySelector('.robot-avatar');
    console.log('机器人头像元素:', robotAvatar);

    // 使用事件委托
    container.addEventListener('click', function(e) {
        console.log('容器点击事件触发:', e.target);
        if (e.target.closest('.robot-avatar')) {
            console.log('机器人头像被点击');
            const chatContainer = container.querySelector('.chat-container');
            chatContainer.style.display = 'flex';
            e.target.closest('.robot-avatar').style.display = 'none';
            
            // 加载聊天组件
            loadChatComponent();
        }
    });

    // 加载聊天组件的函数
    function loadChatComponent() {
        console.log('开始加载聊天组件...');
        fetch(chatUrl)
            .then(response => {
                console.log('收到响应:', response.status, response.statusText);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.text();
            })
            .then(html => {
                console.log('成功获取HTML内容，长度:', html.length);
                // 提取 body 中的内容
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const chatContainer = container.querySelector('.chat-container');
                const chatWidget = doc.querySelector('.chat-widget');
                
                if (chatWidget) {
                    console.log('找到聊天组件元素');
                    // 只获取聊天容器的内容
                    const chatContent = chatWidget.querySelector('.chat-container');
                    if (chatContent) {
                        console.log('找到聊天容器内容');
                        chatContainer.innerHTML = chatContent.innerHTML;
                    }
                    
                    // 添加样式
                    const chatStyles = doc.querySelector('style');
                    if (chatStyles) {
                        console.log('找到样式元素');
                        const newStyle = document.createElement('style');
                        newStyle.textContent = chatStyles.textContent;
                        document.head.appendChild(newStyle);
                    }

                    // 添加脚本
                    const chatScript = doc.querySelector('script');
                    if (chatScript) {
                        console.log('找到脚本元素');
                        const newScript = document.createElement('script');
                        newScript.textContent = chatScript.textContent;
                        document.body.appendChild(newScript);
                    }
                    
                    // 绑定其他事件
                    bindEvents(chatContainer);
                }
            })
            .catch(error => {
                console.error('加载聊天组件失败:', error);
                console.error('错误详情:', {
                    message: error.message,
                    stack: error.stack
                });
            });
    }

    // 绑定其他事件的函数
    function bindEvents(chatContainer) {
        console.log('开始绑定其他事件...');
        
        const closeBtn = chatContainer.querySelector('.chat-header-btn[title="关闭"]');
        const expandBtn = chatContainer.querySelector('.chat-header-btn[title="放大"]');
        const historyBtn = chatContainer.querySelector('#historyBtn');
        const historyList = chatContainer.querySelector('#historyList');
        const chatInput = chatContainer.querySelector('.chat-input');
        const sendBtn = chatContainer.querySelector('.send-btn');
        const newChatBtn = chatContainer.querySelector('.new-chat-btn');

        // 关闭按钮事件
        if (closeBtn) {
            closeBtn.onclick = function() {
                console.log('关闭按钮被点击');
                chatContainer.style.display = 'none';
                container.querySelector('.robot-avatar').style.display = 'flex';
            };
        }

        // 展开/收起事件
        if (expandBtn) {
            expandBtn.onclick = function() {
                console.log('展开/收起按钮被点击');
                chatContainer.classList.toggle('expanded');
                this.querySelector('i').className = chatContainer.classList.contains('expanded') 
                    ? 'ri-fullscreen-exit-line' 
                    : 'ri-fullscreen-line';
                this.title = chatContainer.classList.contains('expanded') ? '收起' : '放大';
            };
        }

        // 历史记录按钮事件
        if (historyBtn && historyList) {
            historyBtn.onclick = function(e) {
                console.log('历史记录按钮被点击');
                e.preventDefault();
                e.stopPropagation();
                historyList.classList.toggle('show');
            };
        }

        // 发送消息事件
        if (sendBtn) {
            sendBtn.onclick = function(e) {
                console.log('发送按钮被点击');
                e.preventDefault();
                if (typeof sendMessage === 'function' && !isLoading) {
                    sendMessage();
                }
            };
        }
        
        // 输入框回车事件
        if (chatInput) {
            chatInput.onkeypress = function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    console.log('输入框回车事件触发');
                    e.preventDefault();
                    if (typeof sendMessage === 'function' && !isLoading) {
                        sendMessage();
                    }
                }
            };
        }

        // 新建对话事件
        if (newChatBtn) {
            newChatBtn.onclick = function() {
                console.log('新建对话按钮被点击');
                if (typeof createNewConversation === 'function') {
                    createNewConversation();
                }
            };
        }

        console.log('其他事件绑定完成');
    }

    // 暴露配置方法
    window.ChatWidget = {
        setConfig: function(newConfig) {
            console.log('设置新配置:', newConfig);
            Object.assign(config, newConfig);
            // 更新基础URL
            baseUrl = `${config.protocol}://${config.host}`;
            console.log('更新后的基础URL:', baseUrl);
        },
        getConfig: function() {
            console.log('获取当前配置');
            return { ...config };
        }
    };
    
    console.log('=== 聊天组件初始化完成 ===');
})(); 