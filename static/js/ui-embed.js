(function() {
    console.log('=== 聊天组件初始化开始 ===');
    
    // 创建配置对象
    const config = {
        protocol: window.location.protocol.replace(':', ''),
        host: window.location.host,
        application_id: null,
        token: null
    };
    console.log('初始配置:', config);

    // 如果存在全局配置，则合并
    if (window.ChatWidget && window.ChatWidget.config) {
        console.log('发现全局配置:', window.ChatWidget.config);
        // 确保用户配置优先
        config.application_id = window.ChatWidget.config.application_id;
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

    // 构建API URL
    const apiUrl = `${baseUrl}/api/chat/applications/${config.application_id}`;
    console.log('API URL:', apiUrl);

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
    
    // 创建机器人头像
    const robotAvatar = document.createElement('div');
    robotAvatar.className = 'robot-avatar';
    robotAvatar.innerHTML = `<img src="${staticBaseUrl}/images/logo.svg" alt="智能客服">`;
    
    // 创建聊天容器
    const chatContainer = document.createElement('div');
    chatContainer.className = 'chat-container';
    
    // 组装容器
    container.appendChild(robotAvatar);
    container.appendChild(chatContainer);
    
    // 添加到页面
    document.body.appendChild(container);
    
    console.log('容器创建完成，DOM结构:', container.outerHTML);
    console.log('机器人头像元素:', robotAvatar);
    
    // 使用事件委托
    container.addEventListener('click', function(e) {
        console.log('容器点击事件触发:', e.target);
        if (e.target.closest('.robot-avatar')) {
            console.log('机器人头像被点击');
            chatContainer.style.display = 'flex';
            e.target.closest('.robot-avatar').style.display = 'none';
            
            // 加载聊天组件
            console.log('准备加载聊天组件...');
            loadChatComponent();
        }
    });

    // 全局状态变量
    let isExpanded = false;
    let isLoading = false;
    let currentConversationId = null;
    let sessionId = null;

    // 工具函数
    function getUrlParam(name) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(name);
    }

    function getBaseUrl() {
        return window.location.origin;
    }

    // 生成会话ID
    function generateSessionId() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0.3 | 0.8);
            return v.toString(16);
        });
    }

    // 初始化会话
    function initializeSession() {
        try {
            // 尝试从localStorage获取sessionId
            const storedSessionId = localStorage.getItem('chat_session_id');
            if (storedSessionId) {
                console.log('使用已存在的会话ID:', storedSessionId);
                sessionId = storedSessionId;
            } else {
                // 如果localStorage不可用（无痕模式），生成新的sessionId
                sessionId = generateSessionId();
                console.log('生成新的会话ID:', sessionId);
                try {
                    localStorage.setItem('chat_session_id', sessionId);
                } catch (e) {
                    console.log('localStorage不可用，使用内存中的sessionId');
                }
            }
        } catch (e) {
            // 如果出现任何错误，生成新的sessionId
            sessionId = generateSessionId();
            console.log('生成新的会话ID（错误恢复）:', sessionId);
        }
    }

    // 加载对话历史
    async function loadConversation(conversationId) {
        if (!sessionId) {
            console.error('会话ID未初始化');
            return;
        }

        try {
            console.log('加载对话历史，会话ID:', sessionId);
            const response = await fetch(`${apiUrl}/conversations/${conversationId}/messages/?session_id=${sessionId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('获取到消息历史:', data);
            
            // 更新聊天内容
            const chatContent = document.querySelector('.chat-content');
            chatContent.innerHTML = data.map(msg => `
                <div class="message-item ${msg.role === 'user' ? 'user-message' : ''}">
                    <div class="message-avatar">
                        <img src="${staticBaseUrl}/images/logo.svg" alt="智能客服" class="avatar">
                    </div>
                    <div class="message-content">
                        ${msg.role === 'assistant' && msg.reasoning ? `
                            <div class="thinking-process">${msg.reasoning}</div>
                        ` : ''}
                        <div class="message-text ${msg.role === 'user' ? 'user' : 'assistant'}">
                            ${msg.content}
                        </div>
                    </div>
                </div>
            `).join('');
            
            currentConversationId = conversationId;
            scrollToBottom();
        } catch (error) {
            console.error('加载对话历史失败:', error);
            showError('加载对话失败');
        }
    }

    // 发送消息
    async function sendMessage() {
        const chatInput = document.querySelector('.chat-input');
        const message = chatInput.value.trim();
        if (!message || isLoading) return;

        isLoading = true;
        
        try {
            if (!sessionId) {
                throw new Error('会话ID未初始化');
            }
            
            // 添加用户消息到界面
            appendMessage('user', message);
            chatInput.value = '';
            // 重置输入框高度
            chatInput.style.height = '44px';
            
            let conversationId = currentConversationId;
            let isFirstMessage = false;
            
            // 如果没有当前对话，先创建新对话
            if (!conversationId) {
                const createResponse = await fetch(`${apiUrl}/conversations/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        session_id: sessionId,
                        message: message
                    })
                });
                
                if (!createResponse.ok) {
                    const errorData = await createResponse.json();
                    throw new Error(errorData.error || '创建对话失败');
                }
                
                const newConversation = await createResponse.json();
                conversationId = newConversation.conversation_id;
                currentConversationId = conversationId;
                isFirstMessage = true;
            }
            
            // 使用stream端点发送消息
            const response = await fetch(`${apiUrl}/conversations/${conversationId}/messages/stream/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    message: message
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || '发送消息失败');
            }

            // 处理流式响应
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            // 添加助手消息占位
            const messageItem = appendMessage('assistant', '', '');
            const messageText = messageItem.querySelector('.message-text');
            const thinkingProcess = messageItem.querySelector('.thinking-process');
            let currentReasoning = '';
            let currentContent = '';
            
            while (true) {
                const {value, done} = await reader.read();
                if (done) {
                    console.log('流式响应结束');
                    // 新建对话后发送第一条消息，流式结束后刷新历史
                    if (isFirstMessage) {
                        await loadConversation(conversationId);
                    }
                    break;
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
                        // 新建对话后发送第一条消息，流式结束后刷新历史
                        if (isFirstMessage) {
                            await loadConversation(conversationId);
                        }
                        return;
                    }
                    
                    // 处理JSON消息
                    try {
                        const jsonData = JSON.parse(data);
                        console.log('解析的JSON数据:', jsonData);
                        
                        // 处理错误消息
                        if (jsonData.error) {
                            console.error('收到错误:', jsonData.error);
                            messageText.textContent = jsonData.error;
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
            }
        } catch (error) {
            console.error('发送消息失败:', error);
            showError(error.message);
        } finally {
            isLoading = false;
        }
    }

    // 添加消息到聊天界面
    function appendMessage(role, content, reasoning = '') {
        const chatContent = document.querySelector('.chat-content');
        const messageItem = document.createElement('div');
        messageItem.className = `message-item ${role === 'user' ? 'user-message' : ''}`;
        
        let messageHtml = `
            <div class="message-avatar">
                <img src="${staticBaseUrl}/images/logo.svg" alt="智能客服" class="avatar">
            </div>
            <div class="message-content">
        `;

        // 始终为助手消息添加思考过程区域
        if (role === 'assistant') {
            messageHtml += `
                <div class="thinking-process" style="display:${reasoning ? 'block' : 'none'}">${reasoning}</div>
            `;
        }

        messageHtml += `
                <div class="message-text ${role === 'user' ? 'user' : 'assistant'}">
                    ${content}
                </div>
            </div>
        `;
        
        messageItem.innerHTML = messageHtml;
        chatContent.appendChild(messageItem);
        scrollToBottom();
        return messageItem;
    }

    // 显示错误消息
    function showError(message) {
        appendMessage('assistant', `错误: ${message}`);
    }

    // 滚动到底部
    function scrollToBottom() {
        const chatContent = document.querySelector('.chat-content');
        chatContent.scrollTo({
            top: chatContent.scrollHeight,
            behavior: 'smooth'
        });
    }

    // 加载聊天组件的函数
    function loadChatComponent() {
        console.log('=== 开始加载聊天组件 ===');
        console.log('请求URL:', chatUrl);
        console.log('当前配置:', {
            baseUrl,
            applicationId: config.application_id,
            protocol: config.protocol,
            host: config.host
        });
        
        // 初始化会话
        initializeSession();
        
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
            console.log('收到响应:', {
                status: response.status,
                statusText: response.statusText,
                headers: Object.fromEntries(response.headers.entries())
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.text();
        })
        .then(html => {
            console.log('成功获取HTML内容，长度:', html.length);
            console.log('HTML内容预览:', html.substring(0, 500) + '...');
            
            // 提取 body 中的内容
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            
            // 获取应用信息
            const applicationInfo = doc.querySelector('title').textContent;
            console.log('应用信息:', applicationInfo);
            
            // 更新机器人头像
            const robotAvatar = container.querySelector('.robot-avatar');
            console.log('当前机器人头像元素:', robotAvatar);
            
            // 直接从HTML中提取SVG内容
            const svgContent = html.match(/<svg[^>]*>[\s\S]*?<\/svg>/);
            console.log('提取到的SVG内容:', svgContent ? svgContent[0] : '未找到SVG');
            
            if (svgContent) {
                console.log('找到SVG内容，准备更新机器人头像');
                robotAvatar.innerHTML = svgContent[0];
                console.log('更新后的机器人头像HTML:', robotAvatar.innerHTML);
            } else {
                console.log('未找到SVG内容，使用默认logo');
                robotAvatar.innerHTML = `<img src="${staticBaseUrl}/images/logo.svg" alt="智能客服">`;
            }
            
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

    // 绑定其他事件
    function bindEvents() {
        console.log('开始绑定事件...');
        const expandBtn = container.querySelector('.chat-header-btn[title="放大"]');
        const closeBtn = container.querySelector('.chat-header-btn[title="关闭"]');
        const chatInput = container.querySelector('.chat-input');
        const sendBtn = container.querySelector('.send-btn');
        const newChatBtn = container.querySelector('.new-chat-btn');
        const historyBtn = container.querySelector('#historyBtn');
        const historyList = container.querySelector('#historyList');

        console.log('找到的元素:', {
            expandBtn: !!expandBtn,
            closeBtn: !!closeBtn,
            chatInput: !!chatInput,
            sendBtn: !!sendBtn,
            newChatBtn: !!newChatBtn,
            historyBtn: !!historyBtn,
            historyList: !!historyList
        });

        // 展开/收起事件
        if (expandBtn) {
            expandBtn.onclick = function() {
                console.log('点击展开按钮');
                isExpanded = !isExpanded;
                const chatContainer = container.querySelector('.chat-container');
                if (chatContainer) {
                    chatContainer.classList.toggle('expanded');
                    this.querySelector('i').className = isExpanded ? 'ri-fullscreen-exit-line' : 'ri-fullscreen-line';
                    this.title = isExpanded ? '收起' : '放大';
                }
            };
        }

        // 关闭按钮事件
        if (closeBtn) {
            closeBtn.onclick = function() {
                console.log('点击关闭按钮');
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

        // 发送消息事件
        if (sendBtn) {
            sendBtn.onclick = function(e) {
                console.log('点击发送按钮');
                e.preventDefault();
                if (!isLoading) {
                    sendMessage();
                }
            };
        }
        
        if (chatInput) {
            chatInput.onkeypress = function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    console.log('按下回车键');
                    e.preventDefault();
                    if (!isLoading) {
                        sendMessage();
                    }
                }
            };
        }

        // 新建对话事件
        if (newChatBtn) {
            newChatBtn.onclick = function() {
                console.log('点击新建对话按钮');
                // 清空聊天内容
                document.querySelector('.chat-content').innerHTML = '';
                // 清空当前对话ID
                currentConversationId = null;
                // 清空输入框
                document.querySelector('.chat-input').value = '';
                // 重置输入框高度
                document.querySelector('.chat-input').style.height = '44px';
                // 聚焦到输入框
                document.querySelector('.chat-input').focus();
            };
        }

        // 历史记录按钮事件
        if (historyBtn) {
            historyBtn.onclick = function(e) {
                console.log('点击历史记录按钮');
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
                    console.log('点击历史记录项:', historyItem.dataset.id);
                    const conversationId = historyItem.dataset.id;
                    loadConversation(conversationId);
                    historyList.classList.remove('show');
                }
            });
        }

        // 点击其他地方关闭历史记录
        document.addEventListener('click', function(e) {
            if (historyList && !historyList.contains(e.target) && !historyBtn.contains(e.target)) {
                historyList.classList.remove('show');
            }
        });

        // 阻止历史记录列表的点击事件冒泡
        if (historyList) {
            historyList.addEventListener('click', function(e) {
                e.stopPropagation();
            });
        }

        // 输入框自动调整高度
        if (chatInput) {
            chatInput.oninput = function() {
                this.style.height = '44px';  // 先重置为默认高度
                const scrollHeight = this.scrollHeight;
                if (scrollHeight > 44) {  // 只有当内容真正超过一行时才调整高度
                    this.style.height = scrollHeight + 'px';
                }
            };
        }

        console.log('事件绑定完成');
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