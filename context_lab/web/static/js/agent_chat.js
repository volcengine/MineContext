/**
 * Agent Chat JavaScript - Context Agent 版本
 * 基于 Context Agent 的智能对话前端逻辑
 */

// 全局状态管理
class AgentChatManager {
    constructor() {
        this.sessionId = null;
        this.workflowId = null;
        this.chatHistory = [];
        this.currentWorkflow = null;
        this.isTyping = false;
        this.isDarkTheme = false;
        this.currentConfirmation = null;
        
        // 文档管理相关状态
        this.currentDocumentId = null;
        this.selectedContent = '';
        this.documents = [];
        
        // 编辑器相关状态
        this.documentEditor = null;
        this.completionHandler = null;
        this.needsSave = false;
        this.completionTimeout = null;
        this.autoSaveTimeout = null;
        this.lastDocumentModified = Date.now(); // 文档最后修改时间戳
        this.autoSaveDelay = 3000; // 自动保存延迟3秒
        
        // 初始化
        this.init();
    }
    
    init() {
        // 确保DOM已经完全加载
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.initializeComponents();
            });
        } else {
            this.initializeComponents();
        }
    }
    
    initializeComponents() {
        this.setupEventListeners();
        this.setupTextSelection();
        this.loadSettings();
        this.loadDocuments();
        this.initEditor();
        console.log('✅ AgentChatManager 初始化完成');
    }
    
    setupEventListeners() {
        // 发送按钮点击
        document.getElementById('chatSendBtn')?.addEventListener('click', () => this.sendMessage());
        
        // 输入框回车发送
        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
            chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                } else if (e.key === 'Enter' && e.ctrlKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
        
        // 页面加载完成后设置焦点
        document.addEventListener('DOMContentLoaded', () => {
            chatInput?.focus();
        });
    }
    
    loadSettings() {
        // 加载主题设置
        const savedTheme = localStorage.getItem('agent_chat_theme');
        if (savedTheme === 'dark') {
            this.toggleTheme();
        }
    }
    
    // 发送消息
    async sendMessage() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        
        if (!message || this.isTyping) {
            return;
        }
        
        // 添加用户消息
        this.addMessage('user', message);
        input.value = '';
        
        // 显示打字指示器
        this.showTypingIndicator();
        
        try {
            // 调用 Context Agent API
            const response = await window.fetch('/api/agent/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: message,
                    context: this.buildContext(),
                    session_id: this.sessionId,
                    user_id: null
                })
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            // 处理流式响应
            await this.handleStreamResponse(response);
            
        } catch (error) {
            console.error('Send message error:', error);
            this.hideTypingIndicator();
            this.addMessage('assistant', '抱歉，网络连接出现问题，请重试。', 'error');
        }
    }
    
    // 处理流式响应
    async handleStreamResponse(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentAiMessage = null;
        
        try {
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) {
                    this.hideTypingIndicator();
                    break;
                }
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // 保留未完成的行
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        
                        if (data === '[DONE]') {
                            continue;
                        }
                        
                        try {
                            const event = JSON.parse(data);
                            await this.handleStreamEvent(event, currentAiMessage);
                            
                        } catch (e) {
                            console.error('Parse event error:', e, data);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Stream response error:', error);
            this.hideTypingIndicator();
            this.addMessage('assistant', '处理响应时出现错误，请重试。', 'error');
        }
    }
    
    // 处理流式事件
    async handleStreamEvent(event) {
        console.log('Stream event:', event);
        
        // 首先处理特殊的全局事件
        if (event.type === 'session_start') {
            this.sessionId = event.session_id;
            // 新会话开始时清空时间线
            this.clearTimeline();
            this.addTimelineEvent('会话开始', 'success');
            console.log('Session started:', this.sessionId);
            return;
        }
        
        // 基于 stage 进行主要的状态处理
        switch (event.stage) {
            case 'init':
                this.updateSessionStatus('活跃', '初始化');
                if (event.content) {
                    this.showTypingIndicator(event.content);
                    this.addTimelineEvent(event.content, 'info');
                }
                break;
                
            case 'intent_analysis':
                this.updateSessionStatus('活跃', '意图分析');
                if (event.type === 'thinking' && event.content) {
                    this.showTypingIndicator(event.content);
                    this.addTimelineEvent(event.content, 'thinking');
                } else if (event.type === 'running' && event.content) {
                    this.addTimelineEvent(event.content, 'info');
                } else if (event.type === 'done' && event.content) {
                    this.addTimelineEvent(event.content, 'success');
                }
                break;
                
            case 'context_gathering':
                this.updateSessionStatus('活跃', '上下文收集');
                if (event.type === 'thinking' && event.content) {
                    this.showTypingIndicator(event.content);
                    this.addTimelineEvent(event.content, 'thinking');
                } else if (event.type === 'running' && event.content) {
                    this.addTimelineEvent(event.content, 'info');
                } else if (event.type === 'done' && event.content) {
                    this.addTimelineEvent(event.content, 'success');
                }
                break;
                
            case 'execution':
                this.updateSessionStatus('活跃', '执行中');
                if (event.type === 'thinking' && event.content) {
                    this.showTypingIndicator(event.content);
                    this.addTimelineEvent(event.content, 'thinking');
                } else if (event.type === 'running' && event.content) {
                    this.addTimelineEvent(event.content, 'info');
                } else if (event.type === 'done' && event.content) {
                    this.addTimelineEvent(event.content, 'success');
                }
                break;
                
            case 'reflection':
                this.updateSessionStatus('活跃', '反思中');
                if (event.type === 'thinking' && event.content) {
                    this.showTypingIndicator(event.content);
                    this.addTimelineEvent(event.content, 'thinking');
                } else if (event.type === 'running' && event.content) {
                    this.addTimelineEvent(event.content, 'info');
                } else if (event.type === 'done' && event.content) {
                    this.addTimelineEvent(event.content, 'success');
                }
                break;
                
            case 'completed':
                // 最终完成状态
                this.hideTypingIndicator();
                this.updateSessionStatus('完成', '已完成');
                this.addTimelineEvent('任务执行完成', 'success');
                if (event.type === 'completed' && event.content) {
                    // 显示最终回复
                    this.addMessage('assistant', event.content);
                }
                break;
                
            case 'failed':
                this.hideTypingIndicator();
                this.updateSessionStatus('错误', '执行失败');
                if (event.content) {
                    this.addMessage('assistant', `错误: ${event.content}`, 'error');
                }
                break;
                
            case 'next':
                // 节点间转换
                if (event.type === 'done' && event.content) {
                    this.addTimelineEvent(event.content, 'success');
                }
                break;
                
            default:
                // 处理其他类型的事件
                if (event.type === 'error') {
                    this.hideTypingIndicator();
                    this.addMessage('assistant', `错误: ${event.content || '未知错误'}`, 'error');
                    this.updateSessionStatus('错误', '执行失败');
                }
                console.log('Unhandled stage:', event.stage, event);
        }
    }
    
    // 显示意图分析结果
    showIntentResult(intent) {
        if (!intent) return;
        
        const message = `📊 <strong>意图分析完成</strong><br>
        • 查询类型: ${intent.type || '未知'}<br>
        • 增强查询: ${intent.enhanced_query || intent.original_query}<br>
        • 置信度: ${(intent.confidence || 0) * 100}%`;
        
        this.addMessage('assistant', message, 'info');
    }
    
    // 显示上下文收集结果
    showContextResult(context) {
        if (!context) return;
        
        const sufficiencyBadge = context.sufficiency === 'sufficient' ? 
            '<span class="badge bg-success">充分</span>' : 
            '<span class="badge bg-warning">不充分</span>';
            
        const message = `📚 <strong>上下文收集完成</strong><br>
        • 收集项数: ${context.count || 0}<br>
        • 充分性: ${sufficiencyBadge}<br>
        ${context.summary ? `• 摘要: ${context.summary}` : ''}`;
        
        this.addMessage('assistant', message, 'info');
    }
    
    // 添加时间线事件
    addTimelineEvent(content, type = 'info') {
        const stepsContainer = document.getElementById('workflowSteps');
        if (!stepsContainer) return;
        
        // 如果是第一个事件，清空空状态
        const emptyWorkflow = stepsContainer.querySelector('.empty-workflow');
        if (emptyWorkflow) {
            stepsContainer.innerHTML = '';
        }
        
        // 创建时间线项
        const timelineItem = document.createElement('div');
        timelineItem.className = `timeline-item timeline-${type}`;
        
        const now = new Date();
        const timeString = now.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        
        timelineItem.innerHTML = `
            <div class="timeline-time">${timeString}</div>
            <div class="timeline-content">${this.escapeHtml(content)}</div>
        `;
        
        stepsContainer.appendChild(timelineItem);
        
        // 滚动到底部
        stepsContainer.scrollTop = stepsContainer.scrollHeight;
    }
    
    // 清空时间线
    clearTimeline() {
        const stepsContainer = document.getElementById('workflowSteps');
        if (stepsContainer) {
            stepsContainer.innerHTML = `
                <div class="empty-workflow">
                    <i class="bi bi-hourglass-split"></i>
                    <p>等待任务开始...</p>
                </div>
            `;
        }
    }
    
    // 构建上下文
    buildContext() {
        // 构建文档上下文
        const DocumentInfo = this.currentDocumentId ? {
            id: this.currentDocumentId,
            title: document.getElementById('documentTitle')?.textContent || '',
            selected_content: this.selectedContent
        } : null;
        
        return {
            chat_history: this.chatHistory.slice(-10), // 只保留最近 10 条消息
            document_context: DocumentInfo,
            session_id: this.sessionId,
            workflow_id: this.workflowId,
            timestamp: new Date().toISOString()
        };
    }
    
    // 添加消息到界面
    addMessage(role, content, type = 'normal') {
        const messagesContainer = document.getElementById('chatMessages');
        if (!messagesContainer) return;
        
        // 移除打字指示器
        if (role === 'assistant') {
            this.hideTypingIndicator();
        }
        
        // 添加到历史记录
        this.chatHistory.push({
            role,
            content,
            timestamp: new Date(),
            type
        });
        
        // 创建消息元素
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const avatar = role === 'user' ? '👤' : '🤖';
        const time = new Date().toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        // 处理消息内容
        let messageContent = content;
        if (role === 'assistant' && typeof marked !== 'undefined') {
            try {
                messageContent = marked.parse(content);
            } catch (e) {
                messageContent = this.escapeHtml(content).replace(/\n/g, '<br>');
            }
        } else {
            messageContent = this.escapeHtml(content).replace(/\n/g, '<br>');
        }
        
        // 根据消息类型添加特殊样式
        let messageClass = 'message-text';
        if (type === 'error') {
            messageClass += ' error-message';
        }
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="bi bi-${role === 'user' ? 'person' : 'robot'}"></i>
            </div>
            <div class="message-content">
                <div class="${messageClass}">${messageContent}</div>
                <div class="message-time">${time}</div>
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        
        // 滚动到底部
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    // 显示打字指示器
    showTypingIndicator(text = 'AI 正在思考中...') {
        this.isTyping = true;
        const messagesContainer = document.getElementById('chatMessages');
        const sendBtn = document.getElementById('chatSendBtn');
        
        // 移除之前的打字指示器（如果存在）
        this.hideTypingIndicator();
        
        // 创建新的打字指示器
        const indicator = document.createElement('div');
        indicator.className = 'message assistant typing-indicator';
        indicator.id = 'typingIndicator';
        
        indicator.innerHTML = `
            <div class="message-avatar">
                <i class="bi bi-robot"></i>
            </div>
            <div class="message-content">
                <div class="message-text">
                    <div class="typing-dots">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                    <div class="typing-text">${this.escapeHtml(text)}</div>
                </div>
            </div>
        `;
        
        // 添加到消息容器底部
        if (messagesContainer) {
            messagesContainer.appendChild(indicator);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        if (sendBtn) {
            sendBtn.disabled = true;
        }
    }
    
    // 隐藏打字指示器
    hideTypingIndicator() {
        this.isTyping = false;
        const indicator = document.getElementById('typingIndicator');
        const sendBtn = document.getElementById('chatSendBtn');
        
        // 移除打字指示器元素
        if (indicator) {
            indicator.remove();
        }
        
        if (sendBtn) {
            sendBtn.disabled = false;
        }
    }
    
    // 更新会话状态
    updateSessionStatus(status, stage) {
        const statusValue = document.getElementById('sessionStatusValue');
        const currentStage = document.getElementById('currentStage');
        
        if (statusValue) {
            statusValue.textContent = status;
        }
        
        if (currentStage) {
            currentStage.textContent = stage;
        }
    }
    
    // 显示工作流计划
    showWorkflowPlan(plan) {
        if (!plan || !plan.steps) return;
        
        this.currentWorkflow = plan;
        const stepsContainer = document.getElementById('workflowSteps');
        const progressContainer = document.getElementById('workflowProgress');
        
        // 清空并显示步骤
        stepsContainer.innerHTML = '';
        
        plan.steps.forEach((step, index) => {
            const stepDiv = document.createElement('div');
            stepDiv.className = 'workflow-step pending';
            stepDiv.id = `workflow-step-${step.step_id}`;
            
            // 添加点击事件显示详情
            stepDiv.addEventListener('click', () => this.showStepDetails(step));
            stepDiv.style.cursor = 'pointer';
            
            const riskIcon = this.getRiskIcon(step.risk_level);
            const agentIcon = this.getAgentIcon(step.agent);
            
            stepDiv.innerHTML = `
                <div class="step-header">
                    <div class="step-title">
                        ${agentIcon} 步骤 ${step.step_id}: ${step.description}
                    </div>
                    <div class="step-status pending">
                        <i class="bi bi-clock"></i>
                        等待中
                    </div>
                </div>
                <div class="step-description">${step.description}</div>
                <div class="step-details">
                    <span><i class="bi bi-person-gear"></i> ${step.agent}</span>
                    <span><i class="bi bi-play-circle"></i> ${step.action}</span>
                    <span>${riskIcon} ${step.risk_level}</span>
                    ${step.estimated_duration ? `<span><i class="bi bi-clock-history"></i> ${step.estimated_duration}</span>` : ''}
                </div>
                <div class="step-progress" style="display: none;">
                    <div class="progress-mini">
                        <div class="progress-bar-mini"></div>
                    </div>
                </div>
            `;
            
            stepsContainer.appendChild(stepDiv);
        });
        
        // 显示进度条
        if (progressContainer) {
            progressContainer.style.display = 'block';
            this.updateProgressBar(0, plan.steps.length);
        }
        
        // 添加计划摘要
        this.addPlanSummary(plan);
    }
    
    // 更新工作流步骤
    updateWorkflowStep(stepId, status, message) {
        const stepElement = document.getElementById(`workflow-step-${stepId}`);
        if (!stepElement) return;
        
        // 更新样式
        stepElement.className = `workflow-step ${status}`;
        
        // 更新状态显示
        const statusElement = stepElement.querySelector('.step-status');
        if (statusElement) {
            statusElement.className = `step-status ${status}`;
            
            let icon = 'bi-clock';
            let text = '等待中';
            
            switch (status) {
                case 'running':
                    icon = 'bi-play-circle';
                    text = '执行中';
                    break;
                case 'completed':
                    icon = 'bi-check-circle';
                    text = '已完成';
                    break;
                case 'failed':
                    icon = 'bi-x-circle';
                    text = '失败';
                    break;
            }
            
            statusElement.innerHTML = `<i class="bi ${icon}"></i> ${text}`;
        }
        
        // 如果有消息，添加到描述中
        if (message) {
            const descElement = stepElement.querySelector('.step-description');
            if (descElement) {
                descElement.textContent = message;
            }
        }
    }
    
    // 更新工作流进度
    updateWorkflowProgress(data) {
        if (!this.currentWorkflow) return;
        
        const currentStep = data.current_step || 0;
        const totalSteps = this.currentWorkflow.steps.length;
        
        this.updateProgressBar(currentStep, totalSteps);
    }
    
    // 更新进度条
    updateProgressBar(current, total) {
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        
        if (progressBar) {
            const percentage = total > 0 ? (current / total) * 100 : 0;
            progressBar.style.width = `${percentage}%`;
        }
        
        if (progressText) {
            progressText.textContent = `${current}/${total}`;
        }
    }
    
    // 处理确认请求
    handleConfirmationRequest(confirmationData) {
        this.currentConfirmation = confirmationData;
        
        // 显示确认模态框
        this.showConfirmationModal(confirmationData);
    }
    
    // 显示确认模态框
    showConfirmationModal(confirmation) {
        const modal = document.getElementById('confirmationModal');
        const modalBody = document.getElementById('confirmationModalBody');
        
        if (!modal || !modalBody) return;
        
        // 构建确认内容
        let content = `
            <div class="confirmation-content">
                <h6><i class="bi bi-info-circle me-2"></i>请求确认</h6>
                <p>${confirmation.description || '系统需要您的确认才能继续执行。'}</p>
        `;
        
        if (confirmation.plan) {
            content += `
                <div class="confirmation-plan">
                    <strong>执行计划:</strong>
                    <ul>
            `;
            
            confirmation.plan.steps?.forEach(step => {
                content += `<li>${step.description} <span class="risk-badge ${step.risk_level}">${step.risk_level}</span></li>`;
            });
            
            content += `
                    </ul>
                    <p><strong>预计时间:</strong> ${confirmation.plan.estimated_time}</p>
                    <p><strong>风险评估:</strong> <span class="risk-badge ${confirmation.plan.risk_assessment}">${confirmation.plan.risk_assessment}</span></p>
                </div>
            `;
        }
        
        content += '</div>';
        
        modalBody.innerHTML = content;
        
        // 显示模态框
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    }
    
    // 批准确认
    async approveConfirmation() {
        if (!this.currentConfirmation) return;
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('confirmationModal'));
        if (modal) {
            modal.hide();
        }
        
        // 显示确认消息
        this.addMessage('assistant', '✅ 您已确认执行，任务将继续进行...', 'info');
        
        // 显示加载状态
        this.showTypingIndicator('正在恢复任务执行...');
        
        await this.sendConfirmationResponse('approve');
    }
    
    // 拒绝确认
    async rejectConfirmation() {
        if (!this.currentConfirmation) return;
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('confirmationModal'));
        if (modal) {
            modal.hide();
        }
        
        // 显示拒绝消息
        this.addMessage('assistant', '❌ 您已拒绝执行，任务已取消。', 'warning');
        
        await this.sendConfirmationResponse('reject', '用户拒绝执行');
    }
    
    // 发送确认响应
    async sendConfirmationResponse(action, reason = null) {
        if (!this.sessionId) return;
        
        try {
            const response = await window.fetch('/api/agent/resume/' + this.workflowId, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    workflow_id: this.workflowId,
                    user_input: reason
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 处理不同类型的响应
                if (result.type === 'task_completed' && result.execution_results) {
                    this.handleExecutionResults(result.execution_results);
                    this.updateSessionStatus('完成', '已完成');
                    this.addMessage('assistant', '🎉 任务执行完成！');
                } else if (result.type === 'cancelled') {
                    this.updateSessionStatus('已取消', '用户取消');
                }
            } else {
                this.addMessage('assistant', `确认处理失败: ${result.error}`, 'error');
            }
            
            // 隐藏加载状态
            this.hideTypingIndicator();
            this.currentConfirmation = null;
            
        } catch (error) {
            console.error('Confirmation response error:', error);
            this.hideTypingIndicator();
            this.addMessage('assistant', '确认请求失败，请重试。', 'error');
        }
    }
    
    // 处理步骤结果
    handleStepResult(result) {
        if (!result) return;
        
        // 如果结果包含具体内容，显示给用户
        if (result.summary) {
            this.addMessage('assistant', result.summary);
        } else if (result.response) {
            this.addMessage('assistant', result.response);
        } else if (typeof result === 'string') {
            this.addMessage('assistant', result);
        }
    }
    
    // 处理工作流完成
    handleWorkflowComplete(data) {
        this.updateSessionStatus('完成', '已完成');
        
        if (!data) {
            this.addMessage('assistant', '✅ 任务已完成');
            return;
        }
        
        // 保存工作流ID
        if (data.workflow_id) {
            this.workflowId = data.workflow_id;
        }
        
        // 显示执行结果
        if (data.execution) {
            if (data.execution.success) {
                // 显示输出
                if (data.execution.outputs && data.execution.outputs.length > 0) {
                    data.execution.outputs.forEach(output => {
                        this.addMessage('assistant', output);
                    });
                } else {
                    this.addMessage('assistant', '✅ 任务执行成功');
                }
            } else {
                // 显示错误
                if (data.execution.errors && data.execution.errors.length > 0) {
                    data.execution.errors.forEach(error => {
                        this.addMessage('assistant', `❌ 错误: ${error}`, 'error');
                    });
                } else {
                    this.addMessage('assistant', '❌ 任务执行失败', 'error');
                }
            }
        }
        
        // 显示反思结果（如果有）
        if (data.reflection) {
            const reflectionMessage = `💭 <strong>反思总结</strong><br>
            • 类型: ${data.reflection.type}<br>
            • 成功率: ${(data.reflection.success_rate || 0) * 100}%<br>
            • 总结: ${data.reflection.summary}`;
            
            if (data.reflection.improvements && data.reflection.improvements.length > 0) {
                const improvements = data.reflection.improvements.join('<br>• ');
                this.addMessage('assistant', `${reflectionMessage}<br><strong>改进建议:</strong><br>• ${improvements}`, 'info');
            } else {
                this.addMessage('assistant', reflectionMessage, 'info');
            }
        }
    }
    
    // 处理执行结果
    handleExecutionResults(results) {
        if (!results || !Array.isArray(results)) return;
        
        results.forEach(result => {
            if (result.success && result.result) {
                this.handleStepResult(result.result);
                
                // 更新对应的步骤状态
                if (result.step_id) {
                    this.updateWorkflowStep(result.step_id, 'completed', '执行成功');
                }
            } else if (!result.success) {
                // 处理失败的步骤
                if (result.step_id) {
                    this.updateWorkflowStep(result.step_id, 'failed', result.error || '执行失败');
                }
            }
        });
    }
    
    // 切换主题
    toggleTheme() {
        this.isDarkTheme = !this.isDarkTheme;
        document.body.classList.toggle('dark-theme', this.isDarkTheme);
        
        // 更新按钮图标
        const themeBtn = document.querySelector('[onclick="toggleTheme()"] i');
        if (themeBtn) {
            themeBtn.className = this.isDarkTheme ? 'bi bi-sun' : 'bi bi-moon';
        }
        
        // 保存设置
        localStorage.setItem('agent_chat_theme', this.isDarkTheme ? 'dark' : 'light');
    }
    
    // === 文档管理功能 ===
    
    // 加载文档列表
    async loadDocuments() {
        const loadingEl = document.getElementById('documentsLoading');
        const listEl = document.getElementById('documentsList');
        
        try {
            if (loadingEl) {
                loadingEl.style.display = 'block';
            }
            
            const response = await fetch('/api/vaults/list');
            const result = await response.json();
            
            if (result.success) {
                this.documents = result.data;
                this.renderDocumentsList(this.documents);
            } else {
                if (listEl) {
                    listEl.innerHTML = '<div class="text-danger p-3">加载失败: ' + (result.error || '未知错误') + '</div>';
                }
            }
        } catch (error) {
            console.error('❌ 加载文档列表异常:', error);
            if (listEl) {
                listEl.innerHTML = '<div class="text-danger p-3">网络错误: ' + (error.message || '未知错误') + '</div>';
            }
        } finally {
            if (loadingEl) {
                loadingEl.style.display = 'none';
            }
        }
    }

    // 渲染文档列表
    renderDocumentsList(docs) {
        const listEl = document.getElementById('documentsList');
        
        if (!listEl) {
            console.error('❌ documentsList 元素未找到');
            return;
        }
        
        if (docs.length === 0) {
            listEl.innerHTML = '<div class="text-muted p-3">暂无文档</div>';
            return;
        }

        const html = docs.map(doc => `
            <div class="document-item" onclick="agentChat.loadDocument(${doc.id})" data-doc-id="${doc.id}">
                <div class="document-title">${this.escapeHtml(doc.title)}</div>
                <div class="document-meta">
                    ${new Date(doc.created_at).toLocaleDateString()} • ${doc.content_length || 0} 字符
                </div>
            </div>
        `).join('');

        listEl.innerHTML = html;

        // 如果有文档，自动加载第一个
        if (docs.length > 0 && !this.currentDocumentId) {
            this.loadDocument(docs[0].id);
        }
    }

    // 加载文档详情 - 直接在编辑器中显示
    async loadDocument(docId) {
        try {
            // 更新选中状态
            document.querySelectorAll('.document-item').forEach(item => {
                item.classList.remove('active');
            });
            const selectedItem = document.querySelector(`[data-doc-id="${docId}"]`);
            if (selectedItem) {
                selectedItem.classList.add('active');
            }

            const response = await fetch(`/api/vaults/${docId}`);
            const result = await response.json();

            if (result.success) {
                this.currentDocumentId = docId;
                const doc = result.data;
                
                // 更新文档标题
                const titleEl = document.getElementById('documentTitle');
                if (titleEl) {
                    titleEl.textContent = doc.title || '未命名文档';
                }
                
                // 直接在编辑器中显示内容
                if (this.documentEditor) {
                    this.documentEditor.setValue(doc.content || '');
                    this.needsSave = false;
                    this.lastDocumentModified = Date.now(); // 重置文档修改时间戳
                    
                    // 取消任何待处理的自动保存
                    if (this.autoSaveTimeout) {
                        clearTimeout(this.autoSaveTimeout);
                        this.autoSaveTimeout = null;
                    }
                    
                    // 启用保存按钮
                    const saveBtn = document.getElementById('saveDocBtn');
                    if (saveBtn) {
                        saveBtn.disabled = true; // 新加载的文档不需要保存
                        saveBtn.innerHTML = '<i class="bi bi-floppy"></i> 保存';
                    }
                    
                    // 刷新编辑器显示
                    setTimeout(() => {
                        this.documentEditor.refresh();
                        this.documentEditor.focus();
                    }, 100);
                }
                
                // 清除选中内容
                this.hideSelectedContent();
                
                console.log(`✅ 已加载文档: ${doc.title}`);
            } else {
                alert('加载文档失败: ' + result.error);
            }
        } catch (error) {
            alert('网络错误: ' + error.message);
        }
    }

    // 文本选择设置
    setupTextSelection() {
        const editorEl = document.getElementById('documentEditor');
        
        if (!editorEl) return;
        
        // 编辑器的文本选择
        editorEl.addEventListener('mouseup', () => this.handleTextSelection());
        editorEl.addEventListener('keyup', (e) => this.handleKeySelection(e));
    }
    
    handleTextSelection() {
        const selection = window.getSelection();
        const selectedText = selection.toString().trim();
        
        if (selectedText && selectedText.length > 3) {
            this.selectedContent = selectedText;
            this.showSelectedContent(selectedText);
        } else {
            this.hideSelectedContent();
        }
    }
    
    handleKeySelection(e) {
        if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) {
            setTimeout(() => this.handleTextSelection(), 10);
        }
    }

    // 显示选中内容
    showSelectedContent(text) {
        const panel = document.getElementById('selectedContentPanel');
        const textEl = document.getElementById('selectedContentText');
        
        if (panel && textEl) {
            textEl.textContent = text.length > 150 ? text.substring(0, 150) + '...' : text;
            panel.style.display = 'block';
        }
    }

    // 隐藏选中内容
    hideSelectedContent() {
        this.selectedContent = '';
        const panel = document.getElementById('selectedContentPanel');
        if (panel) {
            panel.style.display = 'none';
        }
    }

    // 创建新文档
    async createNewDocument() {
        const title = prompt('请输入新文档标题:');
        if (!title || !title.trim()) {
            return;
        }

        try {
            const initialContent = `# ${title.trim()}\n\n开始编写你的内容...`;
            
            const response = await fetch('/api/vaults/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: title.trim(),
                    content: initialContent,
                    document_type: 'vaults'
                })
            });

            const result = await response.json();

            if (result.success) {
                // 刷新文档列表并加载新文档
                await this.loadDocuments();
                this.loadDocument(result.doc_id);
                this.addMessage('assistant', `✅ 已创建新文档: ${title.trim()}`);
            } else {
                alert('创建失败: ' + result.error);
            }
        } catch (error) {
            alert('网络错误: ' + error.message);
        }
    }

    // 删除当前文档
    async deleteCurrentDocument() {
        if (!this.currentDocumentId) {
            alert('请先选择一个文档');
            return;
        }

        const currentDoc = this.documents.find(doc => doc.id === this.currentDocumentId);
        if (!currentDoc) {
            alert('找不到当前文档');
            return;
        }

        if (!confirm(`确定要删除文档 "${currentDoc.title}" 吗？`)) {
            return;
        }

        try {
            const response = await fetch(`/api/vaults/${this.currentDocumentId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.success) {
                // 清空预览（已删除预览面板，这行代码移除）
                this.currentDocumentId = null;
                const titleEl = document.getElementById('documentTitle');
                if (titleEl) {
                    titleEl.textContent = '选择文档开始编辑';
                }
                
                // 刷新文档列表
                this.loadDocuments();
                this.addMessage('assistant', `✅ 已删除文档: ${currentDoc.title}`);
            } else {
                alert('删除失败: ' + result.error);
            }
        } catch (error) {
            alert('网络错误: ' + error.message);
        }
    }
    
    // === 编辑器功能 ===
    
    initEditor() {
        const textarea = document.getElementById('documentEditorTextarea');
        if (!textarea) {
            console.error('❌ 编辑器文本区域未找到，无法初始化编辑器');
            return;
        }
        
        try {
            // 创建CodeMirror编辑器
            this.documentEditor = CodeMirror.fromTextArea(textarea, {
                mode: 'markdown',
                theme: 'default',
                lineNumbers: false,
                lineWrapping: true,
                placeholder: '选择一个文档开始编辑...支持Markdown语法，按Tab键获取智能补全建议',
                extraKeys: {
                    'Tab': (cm) => this.handleTabKey(cm),
                    'Escape': (cm) => this.handleEscapeKey(cm),
                    'Ctrl-S': (cm) => this.saveDocument(),
                    'Cmd-S': (cm) => this.saveDocument(),
                    'Ctrl-Space': (cm) => this.triggerCompletion(cm),
                    'Up': (cm) => this.handleArrowKey(cm, 'up'),
                    'Down': (cm) => this.handleArrowKey(cm, 'down')
                },
                hintOptions: {
                    completeSingle: false,
                    alignWithWord: true
                }
            });
            
            // 编辑器事件监听
            this.documentEditor.on('change', (cm, change) => this.handleEditorChange(cm, change));
            this.documentEditor.on('cursorActivity', (cm) => this.handleCursorActivity(cm));
            
            // 初始化补全处理器
            this.initCompletionHandler();
            
            console.log('✅ 文档编辑器初始化完成');
        } catch (error) {
            console.error('❌ 编辑器初始化失败:', error);
        }
    }
    
    initCompletionHandler() {
        // 初始化补全处理器
        console.log('🔧 开始初始化补全处理器');
        console.log('CompletionHandler类可用:', typeof CompletionHandler !== 'undefined');
        
        if (typeof CompletionHandler !== 'undefined') {
            try {
                this.completionHandler = new CompletionHandler(this);
                console.log('✅ 补全处理器初始化完成:', !!this.completionHandler);
            } catch (error) {
                console.error('❌ 补全处理器初始化失败:', error);
            }
        } else {
            console.warn('⚠️ CompletionHandler类未找到，补全功能将不可用');
        }
    }
    
    // 手动保存文档
    async saveDocument() {
        if (!this.currentDocumentId) {
            console.warn('无法保存：未选择文档');
            return;
        }
        
        // 取消自动保存计划（用户手动保存）
        if (this.autoSaveTimeout) {
            clearTimeout(this.autoSaveTimeout);
            this.autoSaveTimeout = null;
        }
        
        try {
            console.log('💾 执行手动保存');
            this.updateSaveStatus('保存中...', 'saving');
            
            const content = this.documentEditor.getValue();
            const currentDoc = this.documents.find(doc => doc.id === this.currentDocumentId);
            
            if (!currentDoc) {
                alert('找不到当前文档');
                return;
            }
            
            const response = await fetch(`/api/vaults/${this.currentDocumentId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: currentDoc.title,
                    content: content,
                    document_type: 'vaults'
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.needsSave = false;
                
                // 更新本地文档数据
                const docIndex = this.documents.findIndex(doc => doc.id === this.currentDocumentId);
                if (docIndex !== -1) {
                    this.documents[docIndex].content = content;
                }
                
                this.updateSaveStatus('手动保存成功', 'success');
                this.addMessage('assistant', `✅ 文档已保存: ${currentDoc.title}`);
                console.log('✅ 手动保存完成');
            } else {
                this.updateSaveStatus('保存失败', 'error');
                alert('保存失败: ' + result.error);
            }
        } catch (error) {
            this.updateSaveStatus('保存失败', 'error');
            alert('保存时发生网络错误: ' + error.message);
        }
    }
    
    // 编辑器事件处理
    handleEditorChange(cm, change) {
        this.needsSave = true;
        this.lastDocumentModified = Date.now(); // 更新文档修改时间戳
        
        // 启用保存按钮
        const saveBtn = document.getElementById('saveDocBtn');
        if (saveBtn && this.currentDocumentId) {
            saveBtn.disabled = false;
        }
        
        // 启动自动保存（防抖处理）
        this.scheduleAutoSave();
        
        // 如果启用了补全，延迟触发补全（避免频繁请求）
        if (this.completionHandler && change.origin !== 'complete') {
            clearTimeout(this.completionTimeout);
            this.completionTimeout = setTimeout(() => {
                this.completionHandler.triggerCompletion();
            }, 500);
        }
    }
    
    handleCursorActivity(cm) {
        // 光标移动时隐藏补全面板
        if (this.completionHandler && this.completionHandler.isVisible) {
            this.completionHandler.hideCompletion();
        }
    }
    
    // 按键处理
    handleTabKey(cm) {
        console.log('🔥 Tab键被按下！');
        console.log('补全处理器存在:', !!this.completionHandler);
        
        if (this.completionHandler && this.completionHandler.isVisible) {
            console.log('✅ 接受补全建议');
            this.completionHandler.acceptCurrentSuggestion();
            return;
        }
        
        if (this.completionHandler) {
            console.log('🔍 触发补全请求');
            this.completionHandler.triggerCompletion(true);
        } else {
            console.log('❌ 补全处理器不存在，使用默认Tab行为');
            // 默认Tab行为
            cm.replaceSelection('    '); // 4个空格
        }
    }
    
    handleEscapeKey(cm) {
        if (this.completionHandler && this.completionHandler.isVisible) {
            this.completionHandler.hideCompletion();
        }
    }
    
    handleArrowKey(cm, direction) {
        if (this.completionHandler && this.completionHandler.isVisible) {
            if (direction === 'up') {
                this.completionHandler.selectPrevious();
                return;
            } else if (direction === 'down') {
                this.completionHandler.selectNext();
                return;
            }
        }
        
        // 默认箭头键行为
        if (direction === 'up') {
            CodeMirror.commands.goLineUp(cm);
        } else {
            CodeMirror.commands.goLineDown(cm);
        }
    }
    
    triggerCompletion(cm) {
        if (this.completionHandler) {
            this.completionHandler.triggerCompletion(true);
        }
    }
    
    // 获取编辑器实例（供补全处理器使用）
    getEditor() {
        return this.documentEditor;
    }
    
    // 获取文档最后修改时间（供补全处理器使用）
    getLastModifiedTime() {
        return this.lastDocumentModified;
    }
    
    // 计划自动保存
    scheduleAutoSave() {
        if (!this.currentDocumentId) {
            return;
        }
        
        // 清除之前的自动保存计划
        if (this.autoSaveTimeout) {
            clearTimeout(this.autoSaveTimeout);
        }
        
        // 显示自动保存状态
        this.updateSaveStatus('准备自动保存...');
        
        // 设置新的自动保存计划
        this.autoSaveTimeout = setTimeout(() => {
            this.autoSaveDocument();
        }, this.autoSaveDelay);
    }
    
    // 自动保存文档
    async autoSaveDocument() {
        if (!this.needsSave || !this.currentDocumentId) {
            return;
        }
        
        try {
            console.log('🔄 执行自动保存');
            this.updateSaveStatus('自动保存中...');
            
            const content = this.documentEditor.getValue();
            const currentDoc = this.documents.find(doc => doc.id === this.currentDocumentId);
            
            if (!currentDoc) {
                console.warn('找不到当前文档，取消自动保存');
                return;
            }
            
            const response = await fetch(`/api/vaults/${this.currentDocumentId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: currentDoc.title,
                    content: content,
                    document_type: 'vaults'
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.needsSave = false;
                
                // 更新本地文档数据
                const docIndex = this.documents.findIndex(doc => doc.id === this.currentDocumentId);
                if (docIndex !== -1) {
                    this.documents[docIndex].content = content;
                }
                
                this.updateSaveStatus('自动保存成功', 'success');
                console.log('✅ 自动保存完成');
            } else {
                console.error('自动保存失败:', result.error);
                this.updateSaveStatus('自动保存失败', 'error');
            }
        } catch (error) {
            console.error('自动保存异常:', error);
            this.updateSaveStatus('自动保存失败', 'error');
        }
    }
    
    // 更新保存状态显示
    updateSaveStatus(message, type = 'info') {
        const saveBtn = document.getElementById('saveDocBtn');
        if (!saveBtn) return;
        
        // 保存原始状态
        if (!saveBtn.dataset.originalText) {
            saveBtn.dataset.originalText = saveBtn.innerHTML;
        }
        
        let icon = 'bi-hourglass';
        let className = 'btn-outline-success';
        
        switch (type) {
            case 'success':
                icon = 'bi-check';
                className = 'btn-success';
                break;
            case 'error':
                icon = 'bi-exclamation-triangle';
                className = 'btn-danger';
                break;
            case 'saving':
                icon = 'bi-hourglass';
                className = 'btn-warning';
                break;
        }
        
        // 更新按钮
        saveBtn.className = `btn btn-sm ${className}`;
        saveBtn.innerHTML = `<i class="bi ${icon}"></i> ${message}`;
        
        // 如果是成功或错误状态，3秒后恢复原状态
        if (type === 'success' || type === 'error') {
            setTimeout(() => {
                saveBtn.className = 'btn btn-sm btn-outline-success';
                saveBtn.innerHTML = saveBtn.dataset.originalText;
                saveBtn.disabled = this.needsSave ? false : true;
            }, 3000);
        }
    }
    
    // === 编辑器功能结束 ===
    
    // 清空对话
    clearChat() {
        if (confirm('确定要清空当前对话吗？')) {
            this.chatHistory = [];
            this.currentWorkflow = null;
            this.sessionId = null;
            this.workflowId = null;
            
            // 清空界面
            const messagesContainer = document.getElementById('chatMessages');
            if (messagesContainer) {
                // 只保留欢迎消息
                const welcomeMessage = messagesContainer.querySelector('.message.assistant');
                messagesContainer.innerHTML = '';
                if (welcomeMessage) {
                    messagesContainer.appendChild(welcomeMessage);
                }
            }
            
            // 重置时间线
            this.clearTimeline();
            
            // 隐藏进度条
            const progressContainer = document.getElementById('workflowProgress');
            if (progressContainer) {
                progressContainer.style.display = 'none';
            }
            
            // 重置状态
            this.updateSessionStatus('等待中', '-');
        }
    }
    
    // 导出对话
    exportChat() {
        if (this.chatHistory.length === 0) {
            alert('没有对话内容可导出');
            return;
        }
        
        const exportData = {
            session_id: this.sessionId,
            workflow_id: this.workflowId,
            export_time: new Date().toISOString(),
            chat_history: this.chatHistory,
            workflow: this.currentWorkflow
        };
        
        const dataStr = JSON.stringify(exportData, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
        
        const exportFileDefaultName = `agent_chat_${new Date().toISOString().slice(0,10)}.json`;
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
    }
    
    // HTML 转义
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
    
    // 获取风险等级图标
    getRiskIcon(riskLevel) {
        switch (riskLevel) {
            case 'high':
                return '<i class="bi bi-exclamation-triangle-fill text-danger"></i>';
            case 'medium':
                return '<i class="bi bi-exclamation-triangle text-warning"></i>';
            case 'low':
            default:
                return '<i class="bi bi-info-circle text-info"></i>';
        }
    }
    
    // 获取代理图标
    getAgentIcon(agent) {
        switch (agent) {
            case 'content':
                return '<i class="bi bi-file-text text-primary"></i>';
            case 'document':
                return '<i class="bi bi-folder text-success"></i>';
            case 'search':
                return '<i class="bi bi-search text-info"></i>';
            default:
                return '<i class="bi bi-gear text-secondary"></i>';
        }
    }
    
    // 显示步骤详情
    showStepDetails(step) {
        const modal = document.getElementById('taskDetailModal');
        const modalBody = document.getElementById('taskDetailModalBody');
        
        if (!modal || !modalBody) return;
        
        const riskColor = step.risk_level === 'high' ? 'danger' : 
                         step.risk_level === 'medium' ? 'warning' : 'info';
        
        modalBody.innerHTML = `
            <div class="step-detail-content">
                <div class="row">
                    <div class="col-md-8">
                        <h6><i class="bi bi-list-task me-2"></i>步骤详情</h6>
                        <table class="table table-borderless">
                            <tr>
                                <th width="100">步骤ID:</th>
                                <td>${step.step_id}</td>
                            </tr>
                            <tr>
                                <th>描述:</th>
                                <td>${step.description}</td>
                            </tr>
                            <tr>
                                <th>代理:</th>
                                <td>${this.getAgentIcon(step.agent)} ${step.agent}</td>
                            </tr>
                            <tr>
                                <th>操作:</th>
                                <td><code>${step.action}</code></td>
                            </tr>
                            <tr>
                                <th>预计时间:</th>
                                <td>${step.estimated_duration || '未知'}</td>
                            </tr>
                            <tr>
                                <th>风险等级:</th>
                                <td>
                                    <span class="badge bg-${riskColor}">
                                        ${this.getRiskIcon(step.risk_level)} ${step.risk_level}
                                    </span>
                                </td>
                            </tr>
                            <tr>
                                <th>需要确认:</th>
                                <td>
                                    <span class="badge bg-${step.requires_confirmation ? 'warning' : 'success'}">
                                        ${step.requires_confirmation ? '是' : '否'}
                                    </span>
                                </td>
                            </tr>
                            ${step.success_criteria ? `
                            <tr>
                                <th>成功标准:</th>
                                <td>${step.success_criteria}</td>
                            </tr>
                            ` : ''}
                        </table>
                    </div>
                    <div class="col-md-4">
                        <h6><i class="bi bi-gear me-2"></i>参数配置</h6>
                        <pre class="bg-light p-3 rounded"><code>${JSON.stringify(step.params || {}, null, 2)}</code></pre>
                        
                        ${step.dependencies && step.dependencies.length > 0 ? `
                        <h6 class="mt-3"><i class="bi bi-diagram-3 me-2"></i>依赖关系</h6>
                        <div class="dependencies">
                            ${step.dependencies.map(dep => `
                                <span class="badge bg-secondary me-1">步骤 ${dep}</span>
                            `).join('')}
                        </div>
                        ` : ''}
                    </div>
                </div>
                
                ${step.status === 'completed' && step.result ? `
                <div class="mt-3">
                    <h6><i class="bi bi-check-circle me-2 text-success"></i>执行结果</h6>
                    <div class="bg-success bg-opacity-10 p-3 rounded">
                        <pre><code>${JSON.stringify(step.result, null, 2)}</code></pre>
                    </div>
                </div>
                ` : ''}
                
                ${step.status === 'failed' && step.error ? `
                <div class="mt-3">
                    <h6><i class="bi bi-x-circle me-2 text-danger"></i>错误信息</h6>
                    <div class="bg-danger bg-opacity-10 p-3 rounded">
                        <code class="text-danger">${step.error}</code>
                    </div>
                </div>
                ` : ''}
            </div>
        `;
        
        // 显示模态框
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    }
    
    // 添加计划摘要
    addPlanSummary(plan) {
        const summaryMessage = `📋 <strong>任务计划已生成</strong><br>
        • 总步骤数: ${plan.total_steps}<br>
        • 预计时间: ${plan.estimated_time}<br>
        • 风险评估: <span class="badge bg-${plan.risk_assessment === 'high' ? 'danger' : 
                                                   plan.risk_assessment === 'medium' ? 'warning' : 'info'}">${plan.risk_assessment}</span><br>
        • 需要确认: ${plan.requires_confirmation ? '是' : '否'}`;
        
        this.addMessage('assistant', summaryMessage);
    }
}

// 全局实例
let agentChat;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    agentChat = new AgentChatManager();
});

// 全局函数（供 HTML 调用）
function sendMessage() {
    agentChat?.sendMessage();
}

function approveConfirmation() {
    agentChat?.approveConfirmation();
}

function rejectConfirmation() {
    agentChat?.rejectConfirmation();
}

function toggleTheme() {
    agentChat?.toggleTheme();
}

function clearChat() {
    agentChat?.clearChat();
}

function exportChat() {
    agentChat?.exportChat();
}

// 文档管理全局函数
function createNewDocument() {
    agentChat?.createNewDocument();
}

function deleteCurrentDocument() {
    agentChat?.deleteCurrentDocument();
}

// 保存函数
function saveDocument() {
    agentChat?.saveDocument();
}