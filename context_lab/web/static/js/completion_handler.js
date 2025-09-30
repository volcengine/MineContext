/**
 * 智能补全处理器
 * 负责与后端API通信，处理补全建议的显示和交互
 */

class CompletionHandler {
    constructor(noteEditor) {
        this.editor = noteEditor;
        this.cm = noteEditor.getEditor();
        
        // 补全状态
        this.isVisible = false;
        this.currentSuggestions = [];
        this.selectedIndex = 0;
        this.lastTriggerPosition = null;
        this.lastTriggerTime = 0;
        this.requestTimestamp = null; // 请求时的文档时间戳
        this.pendingRequests = new Set(); // 跟踪待处理的请求
        
        // DOM元素
        this.overlay = document.getElementById('completionOverlay');
        this.suggestionsList = document.getElementById('completionSuggestions');
        
        // 配置
        this.config = {
            debounceDelay: 300,
            minTriggerLength: 3,
            maxVisibleSuggestions: 5,
            apiTimeout: 15000  // 增加到15秒，给AI足够的处理时间
        };
        
        // 补全缓存
        this.cache = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5分钟
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.initializeOverlay();
        console.log('CompletionHandler 初始化完成');
    }
    
    setupEventListeners() {
        // 点击其他地方隐藏补全
        document.addEventListener('click', (e) => {
            if (!this.overlay.contains(e.target)) {
                this.hideCompletion();
            }
        });
        
        // 滚动时隐藏补全
        this.cm.on('scroll', () => {
            this.hideCompletion();
        });
        
        // 窗口大小改变时重新定位补全面板
        window.addEventListener('resize', () => {
            if (this.isVisible) {
                this.positionOverlay();
            }
        });
    }
    
    initializeOverlay() {
        if (!this.overlay || !this.suggestionsList) {
            console.error('补全UI元素未找到');
            return;
        }
        
        // 确保overlay初始状态是隐藏的
        this.overlay.style.display = 'none';
    }
    
    /**
     * 触发补全请求
     * @param {boolean} force - 是否强制触发
     */
    async triggerCompletion(force = false) {
        try {
            const cursor = this.cm.getCursor();
            const content = this.cm.getValue();
            
            // 记录触发时的文档修改时间戳
            const documentTimestamp = this.editor.getLastModifiedTime();
            this.requestTimestamp = documentTimestamp;
            
            console.log('🔍 触发补全请求:', {
                force,
                cursorPosition: cursor,
                contentLength: content.length,
                documentId: this.editor.currentDocumentId,
                documentTimestamp: documentTimestamp
            });
            
            // 检查是否应该触发补全
            if (!force && !this.shouldTriggerCompletion(content, cursor)) {
                console.log('❌ 不满足补全触发条件');
                return;
            }
            
            // 防抖处理
            const now = Date.now();
            if (!force && now - this.lastTriggerTime < this.config.debounceDelay) {
                console.log('⏰ 防抖延迟中');
                return;
            }
            
            this.lastTriggerTime = now;
            this.lastTriggerPosition = cursor;
            
            // 生成请求ID用于跟踪
            const requestId = Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            this.pendingRequests.add(requestId);
            
            // 显示加载状态
            this.updateCompletionStatus('正在获取补全建议...(可能需要几秒钟)');
            console.log('📡 发送补全API请求，ID:', requestId);
            
            // 发起API请求
            const suggestions = await this.requestCompletions(content, cursor, requestId);
            
            // 移除请求跟踪
            this.pendingRequests.delete(requestId);
            
            // 检查文档是否在请求期间被修改
            const currentTimestamp = this.editor.getLastModifiedTime();
            if (currentTimestamp > this.requestTimestamp) {
                console.log('⚠️ 文档已被修改，丢弃过期的补全建议', {
                    requestTimestamp: this.requestTimestamp,
                    currentTimestamp: currentTimestamp
                });
                this.hideCompletion();
                this.updateCompletionStatus('文档已更新，重新触发补全');
                return;
            }
            
            if (suggestions && suggestions.length > 0) {
                console.log('✅ 收到补全建议:', suggestions.length, '个');
                
                // 显示建议
                this.displaySuggestions(suggestions, cursor);
                this.updateCompletionStatus('智能补全已就绪');
            } else {
                console.log('❌ 无补全建议');
                this.hideCompletion();
                this.updateCompletionStatus('暂无补全建议');
            }
            
        } catch (error) {
            console.error('💥 触发补全失败:', error);
            this.hideCompletion();
            this.updateCompletionStatus('补全请求失败');
        }
    }
    
    /**
     * 判断是否应该触发补全
     */
    shouldTriggerCompletion(content, cursor) {
        // 获取光标位置
        const cursorIndex = this.cm.indexFromPos(cursor);
        
        // 检查最小触发长度
        if (cursorIndex < this.config.minTriggerLength) {
            return false;
        }
        
        // 获取当前行内容
        const line = this.cm.getLine(cursor.line);
        const charBefore = line[cursor.ch - 1];
        
        // 如果光标前是空白字符，检查是否适合触发补全
        if (/\s/.test(charBefore)) {
            // 在列表项、标题等结构化内容后可以触发
            if (line.match(/^(\s*[-*+]\s+|^\s*\d+\.\s+|^#+\s+)/)) {
                return true;
            }
            // 在段落结束后可以触发
            if (cursor.ch > 2) {
                return true;
            }
            return false;
        }
        
        // 在单词中间不触发
        const charAfter = line[cursor.ch];
        if (charAfter && /\\w/.test(charAfter)) {
            return false;
        }
        
        return true;
    }
    
    /**
     * 请求补全建议
     */
    async requestCompletions(content, cursor, requestId = null) {
        const cursorIndex = this.cm.indexFromPos(cursor);
        // 修复：从editor获取当前文档ID的方式
        const documentId = this.editor.currentDocumentId;
        
        const requestData = {
            text: content,
            cursor_position: cursorIndex,
            document_id: documentId,
            max_suggestions: this.config.maxVisibleSuggestions,
            context: {
                current_line: this.cm.getLine(cursor.line),
                line_number: cursor.line + 1,
                char_position: cursor.ch
            },
            request_timestamp: this.requestTimestamp, // 添加请求时间戳
            request_id: requestId // 添加请求ID
        };
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.config.apiTimeout);
        
        try {
            const response = await window.fetch('/api/completions/suggest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || '补全请求失败');
            }
            
            // 检查响应中的时间戳（如果后端支持）
            if (result.request_timestamp && result.request_timestamp !== this.requestTimestamp) {
                console.log('⚠️ 后端返回的时间戳不匹配，可能是过期的响应');
                return [];
            }
            
            return result.suggestions || [];
            
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('补全请求超时');
            }
            throw error;
        }
    }
    
    /**
     * 显示补全建议
     */
    displaySuggestions(suggestions, cursor) {
        if (!suggestions || suggestions.length === 0) {
            this.hideCompletion();
            return;
        }
        
        this.currentSuggestions = suggestions;
        this.selectedIndex = 0;
        
        // 渲染建议列表
        this.renderSuggestions();
        
        // 定位并显示补全面板
        this.positionOverlay(cursor);
        this.showCompletion();
    }
    
    /**
     * 渲染补全建议
     */
    renderSuggestions() {
        if (!this.suggestionsList) return;
        
        const html = this.currentSuggestions.map((suggestion, index) => {
            const isSelected = index === this.selectedIndex;
            // 修复：处理API返回的建议格式
            const suggestionText = suggestion.text || suggestion.suggestion || '';
            const suggestionType = suggestion.completion_type || suggestion.type || 'semantic';
            const typeClass = this.getCompletionTypeClass(suggestionType);
            
            return `
                <div class="completion-item ${isSelected ? 'selected' : ''}" 
                     data-index="${index}">
                    <div class="completion-text">${this.escapeHtml(suggestionText)}</div>
                    <div class="completion-type ${typeClass}">${this.getCompletionTypeLabel(suggestionType)}</div>
                    ${suggestion.context_used && suggestion.context_used.length > 0 ? 
                        `<div class="completion-context-hint">来源: ${suggestion.context_used.join(', ')}</div>` : 
                        ''}
                </div>
            `;
        }).join('');
        
        this.suggestionsList.innerHTML = html;
        
        // 添加点击事件
        this.suggestionsList.querySelectorAll('.completion-item').forEach((item, index) => {
            item.addEventListener('click', () => {
                this.selectedIndex = index;
                this.acceptCurrentSuggestion();
            });
        });
    }
    
    /**
     * 定位补全面板
     */
    positionOverlay(cursor = null) {
        if (!cursor) {
            cursor = this.cm.getCursor();
        }
        
        const coords = this.cm.cursorCoords(cursor, 'local');
        const editorRect = this.cm.getWrapperElement().getBoundingClientRect();
        
        // 计算绝对位置
        const left = editorRect.left + coords.left;
        const top = editorRect.top + coords.bottom + 5; // 光标下方5px
        
        // 确保不超出视口
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const overlayWidth = 400; // 预估宽度
        const overlayHeight = 200; // 预估高度
        
        let finalLeft = left;
        let finalTop = top;
        
        // 水平位置调整
        if (left + overlayWidth > viewportWidth) {
            finalLeft = viewportWidth - overlayWidth - 10;
        }
        
        // 垂直位置调整
        if (top + overlayHeight > viewportHeight) {
            finalTop = editorRect.top + coords.top - overlayHeight - 5; // 光标上方
        }
        
        this.overlay.style.left = finalLeft + 'px';
        this.overlay.style.top = finalTop + 'px';
    }
    
    /**
     * 显示补全面板
     */
    showCompletion() {
        this.overlay.style.display = 'block';
        this.isVisible = true;
        
        // 添加动画类
        this.overlay.classList.add('fade-in');
        
        setTimeout(() => {
            this.overlay.classList.remove('fade-in');
        }, 200);
    }
    
    /**
     * 隐藏补全面板
     */
    hideCompletion() {
        this.overlay.style.display = 'none';
        this.isVisible = false;
        this.currentSuggestions = [];
        this.selectedIndex = 0;
        this.requestTimestamp = null; // 清除请求时间戳
        
        // 取消所有待处理的请求
        this.pendingRequests.clear();
    }
    
    /**
     * 导航补全选项
     */
    navigateSuggestions(direction) {
        if (!this.isVisible || this.currentSuggestions.length === 0) {
            return;
        }
        
        const oldIndex = this.selectedIndex;
        
        if (direction === 'up') {
            this.selectedIndex = Math.max(0, this.selectedIndex - 1);
        } else if (direction === 'down') {
            this.selectedIndex = Math.min(this.currentSuggestions.length - 1, this.selectedIndex + 1);
        }
        
        if (oldIndex !== this.selectedIndex) {
            this.renderSuggestions();
        }
    }
    
    /**
     * 接受当前选中的补全建议
     */
    acceptCurrentSuggestion() {
        if (!this.isVisible || this.currentSuggestions.length === 0) {
            return;
        }
        
        const suggestion = this.currentSuggestions[this.selectedIndex];
        if (!suggestion) {
            return;
        }
        
        // 修复：正确获取建议文本
        const suggestionText = suggestion.text || suggestion.suggestion || '';
        if (!suggestionText) {
            console.warn('补全建议文本为空');
            return;
        }
        
        // 插入补全文本
        const cursor = this.cm.getCursor();
        this.cm.replaceRange(suggestionText, cursor);
        
        // 移动光标到插入文本的末尾
        const newCursor = {
            line: cursor.line,
            ch: cursor.ch + suggestionText.length
        };
        this.cm.setCursor(newCursor);
        
        // 隐藏补全面板
        this.hideCompletion();
        
        // 聚焦编辑器
        this.cm.focus();
        
        // 发送反馈（用于改进补全质量）
        this.sendFeedback(suggestion, true);
        
        console.log('接受补全:', suggestionText);
    }
    
    /**
     * 发送补全反馈
     */
    async sendFeedback(suggestion, accepted) {
        try {
            const documentId = this.editor.getCurrentDocument()?.id;
            
            await fetch('/api/completions/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    suggestion_text: suggestion.text,
                    document_id: documentId,
                    accepted: accepted,
                    completion_type: suggestion.type
                })
            });
        } catch (error) {
            console.warn('发送补全反馈失败:', error);
        }
    }
    
    /**
     * 生成缓存键
     */
    generateCacheKey(content, cursor) {
        const contextLength = 200; // 使用前200个字符作为上下文
        const cursorIndex = this.cm.indexFromPos(cursor);
        const context = content.substring(Math.max(0, cursorIndex - contextLength), cursorIndex);
        
        // 修复：使用简单的哈希方法代替btoa，避免中文字符编码问题
        const keyString = context + '|' + cursor.line + '|' + cursor.ch;
        let hash = 0;
        for (let i = 0; i < keyString.length; i++) {
            const char = keyString.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // 转换为32位整数
        }
        return 'cache_' + Math.abs(hash).toString(36);
    }
    
    /**
     * 从缓存获取结果
     */
    getFromCache(key) {
        const cached = this.cache.get(key);
        if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
            return cached.data;
        }
        
        // 清理过期缓存
        if (cached) {
            this.cache.delete(key);
        }
        
        return null;
    }
    
    /**
     * 添加到缓存
     */
    addToCache(key, data) {
        // 限制缓存大小
        if (this.cache.size > 50) {
            const oldestKey = this.cache.keys().next().value;
            this.cache.delete(oldestKey);
        }
        
        this.cache.set(key, {
            data: data,
            timestamp: Date.now()
        });
    }
    
    /**
     * 获取补全类型的CSS类
     */
    getCompletionTypeClass(type) {
        switch (type) {
            case 'semantic_continuation':
                return 'semantic_continuation';
            case 'template_completion':
                return 'template_completion';
            case 'reference_suggestion':
                return 'reference_suggestion';
            default:
                return 'context_aware';
        }
    }
    
    /**
     * 获取补全类型的标签
     */
    getCompletionTypeLabel(type) {
        switch (type) {
            case 'semantic_continuation':
                return '语义续写';
            case 'template_completion':
                return '模板补全';
            case 'reference_suggestion':
                return '引用建议';
            case 'context_aware':
                return '智能补全';
            default:
                return '补全建议';
        }
    }
    
    /**
     * 转义HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * 更新补全状态
     */
    updateCompletionStatus(status) {
        if (this.editor.updateCompletionStatus) {
            this.editor.updateCompletionStatus(status);
        }
    }
    
    // 公共API方法
    hasVisibleSuggestions() {
        return this.isVisible && this.currentSuggestions.length > 0;
    }
    
    getCurrentSuggestion() {
        return this.currentSuggestions[this.selectedIndex];
    }
    
    clearCache() {
        this.cache.clear();
    }
    
    getCacheSize() {
        return this.cache.size;
    }
    
    // 获取待处理请求数量
    getPendingRequestsCount() {
        return this.pendingRequests.size;
    }
    
    // 检查是否有效的补全建议（基于时间戳）
    isValidCompletion() {
        if (!this.requestTimestamp) {
            return false;
        }
        const currentTimestamp = this.editor.getLastModifiedTime();
        return currentTimestamp <= this.requestTimestamp;
    }
}