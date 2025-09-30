/**
 * 智能笔记编辑器主类
 * 基于CodeMirror的Markdown编辑器，集成智能补全功能
 */

class NoteEditor {
    constructor() {
        this.editor = null;
        this.currentDocument = null;
        this.documents = [];
        this.isPreviewVisible = false;
        this.completionHandler = null;
        this.needsSave = false;
        
        // 编辑器配置
        this.config = {
            autoSave: true,
            autoSaveInterval: 30000, // 30秒自动保存
            completionEnabled: true,
            completionTriggerDelay: 300, // 300ms后触发补全
            maxSuggestions: 3,
            enabledCompletionTypes: ['semantic_continuation', 'template_completion', 'reference_suggestion']
        };
        
        this.init();
    }
    
    async init() {
        try {
            this.initEditor();
            this.initEventListeners();
            await this.loadDocuments();
            this.initCompletionHandler();
            this.startAutoSave();
            
            console.log('NoteEditor 初始化完成');
        } catch (error) {
            console.error('NoteEditor 初始化失败:', error);
            this.showError('编辑器初始化失败: ' + error.message);
        }
    }
    
    initEditor() {
        const textarea = document.getElementById('noteEditor');
        if (!textarea) {
            throw new Error('找不到编辑器元素');
        }
        
        // 创建CodeMirror编辑器
        this.editor = CodeMirror.fromTextArea(textarea, {
            mode: 'markdown',
            theme: 'default',
            lineNumbers: false,
            lineWrapping: true,
            autofocus: true,
            placeholder: '开始编写你的笔记...支持Markdown语法，按Tab键获取智能补全建议',
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
        this.editor.on('change', (cm, change) => this.handleEditorChange(cm, change));
        this.editor.on('cursorActivity', (cm) => this.handleCursorActivity(cm));
        this.editor.on('focus', (cm) => this.handleEditorFocus(cm));
        this.editor.on('blur', (cm) => this.handleEditorBlur(cm));
        
        console.log('CodeMirror编辑器初始化完成');
    }
    
    initEventListeners() {
        // 文档标题输入
        const titleInput = document.getElementById('documentTitle');
        if (titleInput) {
            titleInput.addEventListener('input', () => this.handleTitleChange());
            titleInput.addEventListener('blur', () => this.saveDocument());
        }
        
        // 设置面板切换
        const settingsBtn = document.querySelector('[onclick="toggleCompletionSettings()"]');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.toggleCompletionSettings());
        }
        
        // 补全设置变更
        document.getElementById('triggerMode')?.addEventListener('change', (e) => {
            this.config.completionEnabled = e.target.value === 'auto';
        });
        
        document.getElementById('maxSuggestions')?.addEventListener('change', (e) => {
            this.config.maxSuggestions = parseInt(e.target.value);
        });
        
        // 预览相关
        window.togglePreview = () => this.togglePreview();
        window.refreshPreview = () => this.updatePreview();
        
        // 文档管理
        window.createNewNote = () => this.createNewDocument();
        window.saveCurrentNote = () => this.saveDocument();
        window.deleteCurrentNote = () => this.deleteCurrentDocument();
        
        console.log('事件监听器初始化完成');
    }
    
    initCompletionHandler() {
        // 初始化补全处理器
        if (typeof CompletionHandler !== 'undefined') {
            this.completionHandler = new CompletionHandler(this);
            console.log('补全处理器初始化完成');
        } else {
            console.warn('CompletionHandler类未找到，补全功能将不可用');
        }
    }
    
    async loadDocuments() {
        try {
            const response = await fetch('/api/vaults/list?limit=100');
            const result = await response.json();
            
            if (result.success) {
                this.documents = result.data;
                this.renderDocumentList();
                
                // 如果有文档，加载第一个
                if (this.documents.length > 0) {
                    await this.loadDocument(this.documents[0].id);
                }
            } else {
                console.error('加载文档列表失败:', result.error);
            }
        } catch (error) {
            console.error('加载文档列表异常:', error);
            this.showError('加载文档失败');
        }
    }
    
    renderDocumentList() {
        const listContainer = document.getElementById('documentList');
        if (!listContainer) return;
        
        if (this.documents.length === 0) {
            listContainer.innerHTML = `
                <div class="empty-state text-center p-4">
                    <i class="bi bi-journal-x text-muted" style="font-size: 2em;"></i>
                    <p class="text-muted mt-2">还没有笔记</p>
                    <button class="btn btn-primary btn-sm" onclick="createNewNote()">创建第一篇笔记</button>
                </div>
            `;
            return;
        }
        
        const html = this.documents.map(doc => `
            <div class="document-item ${this.currentDocument?.id === doc.id ? 'active' : ''}" 
                 onclick="window.noteEditor.loadDocument(${doc.id})" data-doc-id="${doc.id}">
                <div class="doc-title">${this.escapeHtml(doc.title || '未命名文档')}</div>
                <div class="doc-meta">
                    ${doc.created_at ? new Date(doc.created_at).toLocaleDateString() : ''} • 
                    ${doc.content_length || 0} 字符
                </div>
            </div>
        `).join('');
        
        listContainer.innerHTML = html;
    }
    
    async loadDocument(docId) {
        try {
            const response = await fetch(`/api/vaults/${docId}`);
            const result = await response.json();
            
            if (result.success) {
                this.currentDocument = result.data;
                
                // 更新编辑器内容
                this.editor.setValue(this.currentDocument.content || '');
                this.editor.clearHistory(); // 清除撤销历史
                
                // 更新标题
                const titleInput = document.getElementById('documentTitle');
                if (titleInput) {
                    titleInput.value = this.currentDocument.title || '';
                }
                
                // 更新文档列表选中状态
                this.renderDocumentList();
                
                // 更新预览
                this.updatePreview();
                
                // 更新状态
                this.updateEditorStatus();
                
                console.log('文档加载完成:', this.currentDocument.title);
            } else {
                this.showError('加载文档失败: ' + result.error);
            }
        } catch (error) {
            console.error('加载文档异常:', error);
            this.showError('加载文档失败');
        }
    }
    
    async createNewDocument() {
        const title = prompt('请输入新笔记标题:');
        if (!title || !title.trim()) {
            return;
        }
        
        try {
            const response = await fetch('/api/vaults/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: title.trim(),
                    content: `# ${title.trim()}\n\n`,
                    document_type: 'vaults'
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 重新加载文档列表
                await this.loadDocuments();
                // 加载新创建的文档
                await this.loadDocument(result.doc_id);
                this.showSuccess('新笔记创建成功');
            } else {
                this.showError('创建笔记失败: ' + result.error);
            }
        } catch (error) {
            console.error('创建文档异常:', error);
            this.showError('创建笔记失败');
        }
    }
    
    async saveDocument() {
        if (!this.currentDocument) {
            console.warn('没有当前文档，无法保存');
            return;
        }
        
        try {
            const titleInput = document.getElementById('documentTitle');
            const title = titleInput?.value || this.currentDocument.title;
            const content = this.editor.getValue();
            
            const response = await fetch(`/api/vaults/${this.currentDocument.id}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: title,
                    content: content,
                    document_type: 'vaults'
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 更新当前文档对象
                this.currentDocument.title = title;
                this.currentDocument.content = content;
                
                // 更新文档列表
                const docIndex = this.documents.findIndex(d => d.id === this.currentDocument.id);
                if (docIndex !== -1) {
                    this.documents[docIndex] = { ...this.documents[docIndex], title, content };
                    this.renderDocumentList();
                }
                
                this.updateSaveStatus('已保存');
                console.log('文档保存成功');
            } else {
                this.showError('保存失败: ' + result.error);
            }
        } catch (error) {
            console.error('保存文档异常:', error);
            this.showError('保存失败');
        }
    }
    
    async deleteCurrentDocument() {
        if (!this.currentDocument) {
            this.showError('没有选中的文档');
            return;
        }
        
        if (!confirm(`确定要删除笔记"${this.currentDocument.title}"吗？`)) {
            return;
        }
        
        try {
            const response = await fetch(`/api/vaults/${this.currentDocument.id}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 清空编辑器
                this.currentDocument = null;
                this.editor.setValue('');
                
                const titleInput = document.getElementById('documentTitle');
                if (titleInput) {
                    titleInput.value = '';
                }
                
                // 重新加载文档列表
                await this.loadDocuments();
                
                this.showSuccess('文档已删除');
            } else {
                this.showError('删除失败: ' + result.error);
            }
        } catch (error) {
            console.error('删除文档异常:', error);
            this.showError('删除失败');
        }
    }
    
    handleEditorChange(cm, change) {
        // 标记文档为已修改
        this.needsSave = true;
        this.updateSaveStatus('未保存');
        
        // 更新预览（防抖）
        clearTimeout(this.previewUpdateTimer);
        this.previewUpdateTimer = setTimeout(() => {
            this.updatePreview();
        }, 500);
        
        // 触发补全（如果启用）
        if (this.config.completionEnabled && this.completionHandler) {
            clearTimeout(this.completionTimer);
            this.completionTimer = setTimeout(() => {
                this.completionHandler.triggerCompletion();
            }, this.config.completionTriggerDelay);
        }
        
        // 更新统计信息
        this.updateEditorStats();
    }
    
    handleCursorActivity(cm) {
        this.updateCursorPosition();
    }
    
    handleEditorFocus(cm) {
        this.updateCompletionStatus('智能补全已就绪');
    }
    
    handleEditorBlur(cm) {
        // 隐藏补全建议
        if (this.completionHandler) {
            this.completionHandler.hideCompletion();
        }
    }
    
    handleTabKey(cm) {
        // 如果有补全建议，接受补全
        if (this.completionHandler && this.completionHandler.hasVisibleSuggestions()) {
            this.completionHandler.acceptCurrentSuggestion();
            return;
        }
        
        // 否则插入制表符或空格
        if (cm.somethingSelected()) {
            cm.indentSelection('add');
        } else {
            cm.replaceSelection('    '); // 4个空格
        }
    }
    
    handleEscapeKey(cm) {
        // 隐藏补全建议
        if (this.completionHandler) {
            this.completionHandler.hideCompletion();
        }
    }
    
    handleArrowKey(cm, direction) {
        // 如果补全面板可见，导航补全选项
        if (this.completionHandler && this.completionHandler.hasVisibleSuggestions()) {
            this.completionHandler.navigateSuggestions(direction);
            return CodeMirror.Pass;
        }
        
        return CodeMirror.Pass;
    }
    
    triggerCompletion(cm) {
        if (this.completionHandler) {
            this.completionHandler.triggerCompletion(true); // 强制触发
        }
    }
    
    handleTitleChange() {
        this.updateSaveStatus('未保存');
    }
    
    togglePreview() {
        this.isPreviewVisible = !this.isPreviewVisible;
        
        const previewPanel = document.querySelector('.preview-panel');
        const editorCol = document.querySelector('.col-md-6');
        const previewToggle = document.getElementById('previewToggle');
        
        if (this.isPreviewVisible) {
            previewPanel?.classList.remove('d-none');
            editorCol?.classList.remove('col-md-9');
            editorCol?.classList.add('col-md-6');
            if (previewToggle) previewToggle.innerHTML = '<i class="bi bi-eye-slash"></i> 隐藏预览';
        } else {
            previewPanel?.classList.add('d-none');
            editorCol?.classList.remove('col-md-6');
            editorCol?.classList.add('col-md-9');
            if (previewToggle) previewToggle.innerHTML = '<i class="bi bi-eye"></i> 预览';
        }
        
        this.updatePreview();
    }
    
    updatePreview() {
        const previewContent = document.getElementById('previewContent');
        if (!previewContent) return;
        
        const content = this.editor.getValue();
        
        if (!content.trim()) {
            previewContent.innerHTML = `
                <div class="empty-preview text-center p-4">
                    <i class="bi bi-eye-slash text-muted"></i>
                    <p class="text-muted mt-2">开始编辑以查看预览</p>
                </div>
            `;
            return;
        }
        
        try {
            const html = marked.parse(content);
            previewContent.innerHTML = html;
        } catch (error) {
            console.error('Markdown解析失败:', error);
            previewContent.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Markdown解析失败
                </div>
                <pre class="text-muted">${this.escapeHtml(content)}</pre>
            `;
        }
    }
    
    toggleCompletionSettings() {
        const settingsPanel = document.getElementById('completionSettings');
        if (settingsPanel) {
            const isVisible = settingsPanel.style.display !== 'none';
            settingsPanel.style.display = isVisible ? 'none' : 'block';
        }
    }
    
    updateCursorPosition() {
        const cursor = this.editor.getCursor();
        const positionEl = document.getElementById('cursorPosition');
        if (positionEl) {
            positionEl.textContent = `行 ${cursor.line + 1}, 列 ${cursor.ch + 1}`;
        }
    }
    
    updateEditorStats() {
        const content = this.editor.getValue();
        const chars = content.length;
        const words = content.trim() ? content.trim().split(/\s+/).length : 0;
        
        const statsEl = document.getElementById('documentStats');
        if (statsEl) {
            statsEl.textContent = `${chars} 字符, ${words} 词`;
        }
    }
    
    updateSaveStatus(status) {
        const saveStatusEl = document.getElementById('saveStatus');
        if (saveStatusEl) {
            saveStatusEl.textContent = status;
            saveStatusEl.className = status === '已保存' ? 'text-success' : 'text-warning';
        }
    }
    
    updateCompletionStatus(status) {
        const completionStatusEl = document.getElementById('completionStatus');
        if (completionStatusEl) {
            completionStatusEl.textContent = status;
        }
    }
    
    updateEditorStatus() {
        this.updateCursorPosition();
        this.updateEditorStats();
        this.updateSaveStatus('已保存');
    }
    
    startAutoSave() {
        if (this.config.autoSave) {
            setInterval(() => {
                if (this.currentDocument && this.needsSave) {
                    this.saveDocument();
                }
            }, this.config.autoSaveInterval);
        }
    }
    
    showError(message) {
        // 简单的错误显示，可以集成更好的通知系统
        console.error(message);
        alert('错误: ' + message);
    }
    
    showSuccess(message) {
        // 简单的成功显示
        console.log(message);
        // 可以在这里添加成功提示的UI
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // 公共API方法
    getCurrentDocument() {
        return this.currentDocument;
    }
    
    getEditorContent() {
        return this.editor.getValue();
    }
    
    getCursorPosition() {
        return this.editor.getCursor();
    }
    
    getEditor() {
        return this.editor;
    }
}