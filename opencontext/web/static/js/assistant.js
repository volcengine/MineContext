// 智能助手页面 JavaScript

class AssistantChat {
    constructor() {
        this.sessionId = null;
        this.currentWorkflowId = null;
        this.isConnected = false;
        this.eventSource = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateConnectionStatus(false);
        this.initializeChat();
    }

    bindEvents() {
        // 发送按钮事件
        document.getElementById('sendButton').addEventListener('click', () => {
            this.sendMessage();
        });

        // 输入框事件
        const messageInput = document.getElementById('messageInput');
        messageInput.addEventListener('keydown', (event) => {
            this.handleKeyDown(event);
        });

        // 确认对话框事件
        document.getElementById('confirmButton').addEventListener('click', () => {
            if (this.pendingAction) {
                this.pendingAction();
                this.pendingAction = null;
            }
            const modal = bootstrap.Modal.getInstance(document.getElementById('confirmModal'));
            modal.hide();
        });
    }

    handleKeyDown(event) {
        if (event.ctrlKey && event.key === 'Enter') {
            event.preventDefault();
            this.sendMessage();
        }
    }

    async initializeChat() {
        // 直接设置为已连接状态并生成会话ID
        this.updateConnectionStatus(true);
        this.sessionId = this.generateSessionId();
    }

    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
    }

    updateConnectionStatus(connected) {
        this.isConnected = connected;
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.status-text');
        
        if (connected) {
            statusIndicator.className = 'status-indicator online';
            statusText.textContent = '已连接';
        } else {
            statusIndicator.className = 'status-indicator offline';
            statusText.textContent = '未连接';
        }
    }

    async sendMessage() {
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (!message) return;
        if (!this.isConnected) {
            this.addMessage('system', '当前未连接到服务器，请稍后重试');
            return;
        }

        // 清空输入框并添加用户消息
        messageInput.value = '';
        this.addMessage('user', message);
        
        // 显示输入中指示器
        this.showTypingIndicator();
        
        // 重置工作流状态
        this.resetWorkflowStages();

        try {
            // 发送流式请求
            const response = await window.fetch('/api/agent/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: message,
                    session_id: this.sessionId,
                    context: {}
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            await this.handleStreamResponse(response);

        } catch (error) {
            console.error('发送消息失败:', error);
            this.hideTypingIndicator();
            this.addMessage('system', `发送失败: ${error.message}`);
        }
    }

    async handleStreamResponse(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentMessage = '';
        let messageStarted = false;

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            this.handleStreamEvent(data);
                            
                            // 处理消息内容
                            if (data.type === 'content' && data.content) {
                                if (!messageStarted) {
                                    this.hideTypingIndicator();
                                    this.addMessage('assistant', '');
                                    messageStarted = true;
                                }
                                currentMessage += data.content;
                                this.updateLastMessage(currentMessage);
                            }
                        } catch (e) {
                            console.error('解析流数据失败:', e);
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
            this.hideTypingIndicator();
        }
    }

    handleStreamEvent(data) {
        console.log('Stream event:', data);

        // 处理会话开始事件
        if (data.type === 'session_start') {
            if (data.session_id) {
                this.sessionId = data.session_id;
            }
            return;
        }

        // 基于 stage 进行主要的状态处理
        switch (data.stage) {
            case 'init':
                if (data.content) {
                    this.showTypingIndicator(data.content);
                    this.addTimelineEvent(data.content, 'info');
                }
                break;
                
            case 'intent_analysis':
                if (data.type === 'thinking' && data.content) {
                    this.showTypingIndicator(data.content);
                    this.addTimelineEvent(data.content, 'thinking');
                } else if (data.type === 'running' && data.content) {
                    this.addTimelineEvent(data.content, 'info');
                } else if (data.type === 'done' && data.content) {
                    this.addTimelineEvent(data.content, 'success');
                }
                break;
                
            case 'context_gathering':
                if (data.type === 'thinking' && data.content) {
                    this.showTypingIndicator(data.content);
                    this.addTimelineEvent(data.content, 'thinking');
                } else if (data.type === 'running' && data.content) {
                    this.addTimelineEvent(data.content, 'info');
                } else if (data.type === 'done' && data.content) {
                    this.addTimelineEvent(data.content, 'success');
                }
                break;
                
            case 'execution':
                if (data.type === 'thinking' && data.content) {
                    this.showTypingIndicator(data.content);
                    this.addTimelineEvent(data.content, 'thinking');
                } else if (data.type === 'running' && data.content) {
                    this.addTimelineEvent(data.content, 'info');
                } else if (data.type === 'done' && data.content) {
                    this.addTimelineEvent(data.content, 'success');
                }
                break;
                
            case 'reflection':
                if (data.type === 'thinking' && data.content) {
                    this.showTypingIndicator(data.content);
                    this.addTimelineEvent(data.content, 'thinking');
                } else if (data.type === 'running' && data.content) {
                    this.addTimelineEvent(data.content, 'info');
                } else if (data.type === 'done' && data.content) {
                    this.addTimelineEvent(data.content, 'success');
                }
                break;
                
            case 'completed':
                // 最终完成状态
                this.hideTypingIndicator();
                this.addTimelineEvent('任务执行完成', 'success');
                if (data.type === 'completed' && data.content) {
                    // 显示最终回复
                    this.addMessage('assistant', data.content);
                }
                break;
                
            case 'failed':
                this.hideTypingIndicator();
                this.addTimelineEvent('执行失败', 'error');
                if (data.content) {
                    this.addMessage('assistant', `错误: ${data.content}`, 'error');
                }
                break;
                
            case 'next':
                // 节点间转换
                if (data.type === 'done' && data.content) {
                    this.addTimelineEvent(data.content, 'success');
                }
                break;
                
            default:
                // 处理其他类型的事件
                if (data.type === 'error') {
                    this.hideTypingIndicator();
                    this.addMessage('assistant', `错误: ${data.content || '未知错误'}`, 'error');
                    this.addTimelineEvent(`错误: ${data.content || '未知错误'}`, 'error');
                }
                console.log('Unhandled stage:', data.stage, data);
        }
    }

    resetWorkflowStages() {
        // 清空时间线
        this.clearTimeline();
    }

    addTimelineEvent(content, type = 'info') {
        const timelineContainer = document.getElementById('timelineContainer');
        if (!timelineContainer) return;

        // 如果是第一个事件，隐藏空状态
        const emptyElement = document.getElementById('timelineEmpty');
        if (emptyElement) {
            emptyElement.style.display = 'none';
        }

        const timelineItem = document.createElement('div');
        timelineItem.className = 'timeline-item';

        const timelineContent = document.createElement('div');
        timelineContent.className = 'timeline-content';

        const timelineText = document.createElement('div');
        timelineText.className = 'timeline-text';
        timelineText.textContent = content;

        const timelineTime = document.createElement('div');
        timelineTime.className = 'timeline-time';
        timelineTime.textContent = new Date().toLocaleTimeString();

        const timelineDot = document.createElement('div');
        timelineDot.className = `timeline-dot ${type}`;

        timelineContent.appendChild(timelineText);
        timelineContent.appendChild(timelineTime);
        timelineItem.appendChild(timelineDot);
        timelineItem.appendChild(timelineContent);

        timelineContainer.appendChild(timelineItem);

        // 滚动到底部
        timelineContainer.scrollTop = timelineContainer.scrollHeight;
    }

    clearTimeline() {
        const timelineContainer = document.getElementById('timelineContainer');
        if (!timelineContainer) return;

        // 清空所有时间线项目
        const timelineItems = timelineContainer.querySelectorAll('.timeline-item');
        timelineItems.forEach(item => item.remove());

        // 显示空状态
        const emptyElement = document.getElementById('timelineEmpty');
        if (emptyElement) {
            emptyElement.style.display = 'block';
        }
    }

    addMessage(type, content) {
        const messagesContainer = document.getElementById('chatMessages');
        
        // 如果是第一条消息，移除欢迎消息
        const welcomeMessage = messagesContainer.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.style.display = 'none';
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        if (type === 'system') {
            contentDiv.style.background = '#fff3cd';
            contentDiv.style.color = '#856404';
            contentDiv.style.border = '1px solid #ffeaa7';
        }
        
        if (content) {
            contentDiv.innerHTML = this.formatMessage(content);
        }
        
        const metaDiv = document.createElement('div');
        metaDiv.className = 'message-meta';
        metaDiv.textContent = new Date().toLocaleTimeString();
        
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(metaDiv);
        messagesContainer.appendChild(messageDiv);
        
        // 滚动到底部
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        return messageDiv;
    }

    updateLastMessage(content) {
        const messages = document.querySelectorAll('.message');
        const lastMessage = messages[messages.length - 1];
        if (lastMessage) {
            const contentDiv = lastMessage.querySelector('.message-content');
            if (contentDiv) {
                contentDiv.innerHTML = this.formatMessage(content);
            }
        }
    }

    formatMessage(content) {
        // 如果有 marked 库，使用 markdown 渲染
        if (typeof marked !== 'undefined') {
            return marked.parse(content);
        }
        
        // 简单的文本格式化
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>');
    }

    showTypingIndicator(message = 'AI正在思考') {
        const messagesContainer = document.getElementById('chatMessages');
        
        // 移除之前的输入指示器
        const existingIndicator = document.getElementById('typingIndicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.id = 'typingIndicator';
        
        typingDiv.innerHTML = `
            <span>${message}</span>
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    clearChat() {
        this.showConfirmDialog('确定要清空所有对话记录吗？', () => {
            const messagesContainer = document.getElementById('chatMessages');
            messagesContainer.innerHTML = `
                <div class="welcome-message">
                    <div class="welcome-icon">
                        <i class="bi bi-robot"></i>
                    </div>
                    <div class="welcome-text">
                        <h5>您好！我是智能助手</h5>
                        <p>我可以帮助您处理各种任务，包括：</p>
                        <ul>
                            <li>回答问题和提供信息</li>
                            <li>分析和处理文档内容</li>
                            <li>协助完成复杂任务</li>
                            <li>提供智能建议和解决方案</li>
                        </ul>
                        <p>请输入您的问题或需求，我将为您提供帮助。</p>
                    </div>
                </div>
            `;
            this.resetWorkflowStages();
            this.sessionId = this.generateSessionId();
        });
    }

    exportChat() {
        const messages = document.querySelectorAll('.message');
        let exportContent = '# 智能助手对话记录\n\n';
        exportContent += `导出时间: ${new Date().toLocaleString()}\n\n`;

        messages.forEach(message => {
            const type = message.classList.contains('user') ? '用户' : 
                        message.classList.contains('assistant') ? '助手' : '系统';
            const content = message.querySelector('.message-content').textContent;
            const time = message.querySelector('.message-meta').textContent;
            
            exportContent += `## ${type} (${time})\n\n${content}\n\n`;
        });

        // 下载文件
        const blob = new Blob([exportContent], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `智能助手对话记录_${new Date().toISOString().slice(0, 10)}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    showConfirmDialog(message, callback) {
        const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
        document.getElementById('confirmModalBody').textContent = message;
        this.pendingAction = callback;
        modal.show();
    }
}

// 全局函数
function sendMessage() {
    if (window.assistantChat) {
        window.assistantChat.sendMessage();
    }
}

function clearTimeline() {
    if (window.assistantChat) {
        window.assistantChat.clearTimeline();
    }
}

function clearChat() {
    if (window.assistantChat) {
        window.assistantChat.clearChat();
    }
}

function exportChat() {
    if (window.assistantChat) {
        window.assistantChat.exportChat();
    }
}

function handleKeyDown(event) {
    if (window.assistantChat) {
        window.assistantChat.handleKeyDown(event);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    window.assistantChat = new AssistantChat();
});