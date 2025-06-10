(function() {
    // 创建配置对象
    const config = {
        protocol: window.location.protocol.replace(':', ''),
        host: window.location.host,
        application_id: 1,
        token: 'your-token-here'
    };

    // 如果存在全局配置，则合并
    if (window.ChatWidget && window.ChatWidget.config) {
        // 确保用户配置优先
        config.application_id = window.ChatWidget.config.application_id || config.application_id;
        config.protocol = window.ChatWidget.config.protocol || config.protocol;
        config.host = window.ChatWidget.config.host || config.host;
        config.token = window.ChatWidget.config.token || config.token;
    }

    // 检查是否提供了应用ID
    if (!config.application_id) {
        console.error('请提供应用ID (application_id)');
        return;
    }

    // 构建基础URL
    const baseUrl = `${config.protocol}://${config.host}`;
    console.log('基础URL:', baseUrl);

    // 构建聊天组件URL
    const chatUrl = `${baseUrl}/api/chat/design/${config.application_id}/`;
    console.log('聊天组件URL:', chatUrl);

    // 生成会话ID
    function generateSessionId() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    // 初始化会话
    let sessionId = localStorage.getItem('chat_session_id') || generateSessionId();
    localStorage.setItem('chat_session_id', sessionId);
    console.log('当前会话ID:', sessionId);

    // 创建样式
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

    // 创建容器
    const container = document.createElement('div');
    container.className = 'chat-widget';
    container.innerHTML = `
        <div class="robot-avatar">
            <img src="https://maxkb.gongjuyuan.com/ui/MaxKB.gif" alt="智能客服">
        </div>
        <div class="chat-container"></div>
    `;
    document.body.appendChild(container);

    // 加载聊天组件
    fetch(chatUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.text();
        })
        .then(html => {
            // 提取 body 中的内容
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const chatContainer = container.querySelector('.chat-container');
            const chatWidget = doc.querySelector('.chat-widget');
            
            if (chatWidget) {
                // 只获取聊天容器的内容
                const chatContent = chatWidget.querySelector('.chat-container');
                if (chatContent) {
                    chatContainer.innerHTML = chatContent.innerHTML;
                }
                
                // 添加样式
                const chatStyles = doc.querySelector('style');
                if (chatStyles) {
                    const newStyle = document.createElement('style');
                    newStyle.textContent = chatStyles.textContent;
                    document.head.appendChild(newStyle);
                }

                // 添加脚本
                const chatScript = doc.querySelector('script');
                if (chatScript) {
                    const newScript = document.createElement('script');
                    newScript.textContent = chatScript.textContent;
                    document.body.appendChild(newScript);
                }
                
                // 重新绑定事件
                const robotAvatar = container.querySelector('.robot-avatar');
                const closeBtn = chatContainer.querySelector('.chat-header-btn[title="关闭"]');
                const expandBtn = chatContainer.querySelector('.chat-header-btn[title="放大"]');
                const historyBtn = chatContainer.querySelector('#historyBtn');
                const historyList = chatContainer.querySelector('#historyList');
                const chatInput = chatContainer.querySelector('.chat-input');
                const sendBtn = chatContainer.querySelector('.send-btn');
                const newChatBtn = chatContainer.querySelector('.new-chat-btn');

                // 机器人头像点击事件
                robotAvatar.onclick = function() {
                    chatContainer.style.display = 'flex';
                    robotAvatar.style.display = 'none';
                    // 初始化会话并加载对话列表
                    if (typeof initializeSession === 'function') {
                        initializeSession();
                    }
                    if (typeof loadConversations === 'function') {
                        loadConversations();
                    }
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

                // 发送消息事件
                sendBtn.onclick = function(e) {
                    e.preventDefault();
                    if (typeof sendMessage === 'function' && !isLoading) {
                        const message = chatInput.value.trim();
                        if (!message) return;

                        console.log('准备发送消息:', {
                            message,
                            sessionId,
                            currentConversationId
                        });

                        // 添加用户消息到界面
                        appendMessage('user', message);
                        chatInput.value = '';
                        // 重置输入框高度
                        chatInput.style.height = '44px';

                        // 如果没有当前对话，先创建新对话
                        if (!currentConversationId) {
                            const createUrl = `${baseUrl}/api/chat/applications/${config.application_id}/conversations/`;
                            const createBody = {
                                session_id: sessionId,
                                message: message
                            };
                            
                            console.log('创建新对话:', {
                                url: createUrl,
                                body: createBody
                            });

                            fetch(createUrl, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify(createBody)
                            })
                            .then(response => {
                                console.log('创建对话响应状态:', response.status);
                                if (!response.ok) {
                                    return response.text().then(text => {
                                        throw new Error(`创建对话失败: ${text}`);
                                    });
                                }
                                return response.json();
                            })
                            .then(data => {
                                console.log('创建对话成功:', data);
                                currentConversationId = data.conversation_id;
                                // 发送消息到新对话
                                sendMessageToConversation(currentConversationId, message);
                            })
                            .catch(error => {
                                console.error('创建对话失败:', error);
                                showError('创建对话失败: ' + error.message);
                            });
                        } else {
                            // 直接发送消息到现有对话
                            sendMessageToConversation(currentConversationId, message);
                        }
                    }
                };
                
                // 发送消息到对话
                function sendMessageToConversation(conversationId, message) {
                    isLoading = true;
                    const streamUrl = `${baseUrl}/api/chat/applications/${config.application_id}/conversations/${conversationId}/messages/stream/`;
                    const streamBody = {
                        session_id: sessionId,
                        message: message
                    };

                    console.log('发送消息到对话:', {
                        url: streamUrl,
                        body: streamBody
                    });

                    fetch(streamUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(streamBody)
                    })
                    .then(response => {
                        console.log('发送消息响应状态:', response.status);
                        if (!response.ok) {
                            return response.text().then(text => {
                                throw new Error(`发送消息失败: ${text}`);
                            });
                        }
                        return response.body.getReader();
                    })
                    .then(reader => {
                        const decoder = new TextDecoder();
                        let buffer = '';
                        
                        // 添加助手消息占位
                        const messageItem = appendMessage('assistant', '', '');
                        const messageText = messageItem.querySelector('.message-text');
                        const thinkingProcess = messageItem.querySelector('.thinking-process');
                        let currentReasoning = '';
                        let currentContent = '';

                        function processStream() {
                            reader.read().then(({value, done}) => {
                                if (done) {
                                    console.log('流式响应结束');
                                    isLoading = false;
                                    return;
                                }

                                const chunk = decoder.decode(value, {stream: true});
                                console.log('收到数据块:', chunk);
                                
                                buffer += chunk;
                                const lines = buffer.split('\n');
                                buffer = lines.pop();
                                
                                for (const line of lines) {
                                    if (!line.startsWith('data: ')) continue;
                                    
                                    const data = line.slice(6).trim();
                                    if (!data) continue;
                                    
                                    // 处理[DONE]消息
                                    if (data === '[DONE]') {
                                        console.log('收到完成标记');
                                        isLoading = false;
                                        return;
                                    }
                                    
                                    // 处理JSON消息
                                    try {
                                        const jsonData = JSON.parse(data);
                                        console.log('解析的JSON数据:', jsonData);
                                        
                                        // 处理错误消息
                                        if (jsonData.error) {
                                            console.error('收到错误:', jsonData.error);
                                            messageText.textContent = `错误: ${jsonData.error}`;
                                            continue;
                                        }
                                        
                                        // 处理reasoning_content
                                        if (jsonData.reasoning_content) {
                                            currentReasoning += jsonData.reasoning_content;
                                            if (thinkingProcess) {
                                                thinkingProcess.style.display = 'block';
                                                thinkingProcess.innerHTML = currentReasoning.replace(/\n+/g, '<br>');
                                                scrollToBottom();
                                            }
                                        }
                                        
                                        // 处理content
                                        if (jsonData.content) {
                                            currentContent += jsonData.content;
                                            messageText.innerHTML = currentContent.replace(/\n+/g, '<br>');
                                            scrollToBottom();
                                        }
                                    } catch (e) {
                                        console.error('解析响应数据失败:', e, '原始数据:', data);
                                    }
                                }
                                
                                processStream();
                            });
                        }
                        
                        processStream();
                    })
                    .catch(error => {
                        console.error('发送消息失败:', error);
                        showError('发送消息失败: ' + error.message);
                        isLoading = false;
                    });
                }

                // 输入框回车事件
                chatInput.onkeypress = function(e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        if (typeof sendMessage === 'function' && !isLoading) {
                            sendMessage();
                        }
                    }
                };

                // 新建对话事件
                newChatBtn.onclick = function() {
                    if (typeof createNewConversation === 'function') {
                        createNewConversation();
                    }
                };
            }
        })
        .catch(error => {
            console.error('加载聊天组件失败:', error);
        });

    // 暴露配置方法
    window.ChatWidget = {
        setConfig: function(newConfig) {
            Object.assign(config, newConfig);
            // 更新基础URL
            baseUrl = `${config.protocol}://${config.host}`;
        },
        getConfig: function() {
            return { ...config };
        }
    };
})(); 