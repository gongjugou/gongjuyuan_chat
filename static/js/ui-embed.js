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
        fetch(chatUrl, {
            method: 'GET',
            headers: {
                'Accept': 'text/html',
                'Content-Type': 'text/html',
            },
            credentials: 'include',
            mode: 'cors'
        })
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
                    // 修改脚本内容，替换API URL和所有API请求
                    let scriptContent = chatScript.textContent;
                    
                    // 替换API URL
                    scriptContent = scriptContent.replace(
                        /const apiUrl = .*?;/,
                        `const apiUrl = '${baseUrl}';`
                    );

                    // 替换所有fetch请求中的URL
                    scriptContent = scriptContent.replace(
                        /fetch\(`\${apiUrl}\/api\/chat\/applications\/\${applicationId}\/conversations\/`/g,
                        `fetch(\`${baseUrl}/api/chat/applications/\${applicationId}/conversations/\``
                    );
                    scriptContent = scriptContent.replace(
                        /fetch\(`\${apiUrl}\/api\/chat\/applications\/\${applicationId}\/conversations\/\${conversationId}\/messages\/`/g,
                        `fetch(\`${baseUrl}/api/chat/applications/\${applicationId}/conversations/\${conversationId}/messages/\``
                    );
                    scriptContent = scriptContent.replace(
                        /fetch\(`\${apiUrl}\/api\/chat\/applications\/\${applicationId}\/conversations\/\${conversationId}\/messages\/stream\/`/g,
                        `fetch(\`${baseUrl}/api/chat/applications/\${applicationId}/conversations/\${conversationId}/messages/stream/\``
                    );
                    scriptContent = scriptContent.replace(
                        /fetch\(`\${apiUrl}\/api\/chat\/applications\/\${applicationId}\/`/g,
                        `fetch(\`${baseUrl}/api/chat/applications/\${applicationId}/\``
                    );

                    // 添加全局变量和session_id生成函数
                    scriptContent = `
                        // 全局配置
                        window.ChatWidgetConfig = {
                            baseUrl: '${baseUrl}',
                            applicationId: ${config.application_id}
                        };

                        // 生成session_id
                        function generateSessionId() {
                            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                                const r = Math.random() * 16 | 0;
                                const v = c === 'x' ? r : (r & 0x3 | 0x8);
                                return v.toString(16);
                            });
                        }

                        // 获取或创建session_id
                        const chatSessionId = localStorage.getItem('chat_session_id') || generateSessionId();
                        try {
                            localStorage.setItem('chat_session_id', chatSessionId);
                        } catch (e) {
                            console.log('localStorage不可用，使用内存中的sessionId');
                        }

                        // 修改所有fetch请求，添加session_id
                        ${scriptContent.replace(
                            /body: JSON\.stringify\(\{([^}]*)\}\)/g,
                            'body: JSON.stringify({$1, session_id: chatSessionId})'
                        )}
                    `;

                    newScript.textContent = scriptContent;
                    document.body.appendChild(newScript);
                }
                
                // 绑定其他事件
                bindEvents();
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

    // 绑定事件
    function bindEvents() {
        console.log('开始绑定其他事件...');
        
        // 获取所有需要的元素
        const chatInput = container.querySelector('.chat-input');
        const sendBtn = container.querySelector('.send-btn');
        const newChatBtn = container.querySelector('.new-chat-btn');
        const historyBtn = container.querySelector('#historyBtn');
        const historyList = container.querySelector('#historyList');
        const expandBtn = container.querySelector('.chat-header-btn[title="放大"]');
        const closeBtn = container.querySelector('.chat-header-btn[title="关闭"]');

        // 发送消息事件
        if (sendBtn) {
            sendBtn.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('发送按钮被点击');
                if (!isLoading) {
                    sendMessage();
                }
            };
        }
        
        // 输入框回车事件
        if (chatInput) {
            chatInput.onkeypress = function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    console.log('输入框回车事件触发');
                    if (!isLoading) {
                        sendMessage();
                    }
                }
            };
        }

        // 新建对话事件
        if (newChatBtn) {
            newChatBtn.onclick = function() {
                // 清空聊天内容
                const chatContent = container.querySelector('.chat-content');
                if (chatContent) {
                    chatContent.innerHTML = '';
                }
                // 清空当前对话ID
                currentConversationId = null;
                // 清空输入框
                if (chatInput) {
                    chatInput.value = '';
                    chatInput.style.height = '44px';
                    chatInput.focus();
                }
            };
        }

        // 历史记录按钮事件
        if (historyBtn && historyList) {
            historyBtn.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                historyList.classList.toggle('show');
            };
        }

        // 点击历史记录项
        if (historyList) {
            historyList.addEventListener('click', function(e) {
                const historyItem = e.target.closest('.history-item');
                if (historyItem) {
                    const conversationId = historyItem.dataset.id;
                    loadConversation(conversationId);
                    historyList.classList.remove('show');
                }
            });
        }

        // 展开/收起事件
        if (expandBtn) {
            expandBtn.onclick = function() {
                isExpanded = !isExpanded;
                const chatContainer = container.querySelector('.chat-container');
                if (chatContainer) {
                    chatContainer.classList.toggle('expanded');
                }
                this.querySelector('i').className = isExpanded ? 'ri-fullscreen-exit-line' : 'ri-fullscreen-line';
                this.title = isExpanded ? '收起' : '放大';
            };
        }

        // 关闭按钮事件
        if (closeBtn) {
            closeBtn.onclick = function() {
                const chatContainer = container.querySelector('.chat-container');
                const robotAvatar = container.querySelector('.robot-avatar');
                if (chatContainer && robotAvatar) {
                    chatContainer.style.display = 'none';
                    robotAvatar.style.display = 'flex';
                    if (isExpanded) {
                        isExpanded = false;
                        chatContainer.classList.remove('expanded');
                        const expandBtn = container.querySelector('.chat-header-btn[title="放大"]');
                        if (expandBtn) {
                            expandBtn.querySelector('i').className = 'ri-fullscreen-line';
                            expandBtn.title = '放大';
                        }
                    }
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