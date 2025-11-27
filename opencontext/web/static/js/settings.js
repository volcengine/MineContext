// Settings page JavaScript

let currentPrompts = {};
let selectedPromptKey = '';

// Toast notification helper
function showToast(message, isError = false) {
    const toastEl = document.getElementById('settingsToast');
    const toastBody = document.getElementById('toastMessage');
    toastBody.textContent = message;
    toastEl.classList.remove('bg-success', 'bg-danger');
    toastEl.classList.add(isError ? 'bg-danger' : 'bg-success');
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
}

// ==================== 截图捕获设置 ====================

async function loadCaptureSettings() {
    try {
        const response = await fetch('/api/settings/general');
        const data = await response.json();

        if (data.code === 0 && data.data) {
            const capture = data.data.capture || {};
            document.getElementById('screenshot_enabled').checked = capture.screenshot?.enabled || false;
            document.getElementById('screenshot_interval').value = capture.screenshot?.capture_interval || 5;
            document.getElementById('screenshot_path').value = capture.screenshot?.storage_path || '';

            document.getElementById('vault_enabled').checked = capture.vault_document_monitor?.enabled || false;
            document.getElementById('vault_interval').value = capture.vault_document_monitor?.monitor_interval || 30;
            document.getElementById('vault_initial_scan').checked = capture.vault_document_monitor?.initial_scan !== false;
        }
    } catch (error) {
        console.error('加载截图设置失败:', error);
        showToast('加载截图设置失败', true);
    }
}

document.getElementById('captureForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const settings = {
        capture: {
            screenshot: {
                enabled: document.getElementById('screenshot_enabled').checked,
                capture_interval: parseInt(document.getElementById('screenshot_interval').value),
                storage_path: document.getElementById('screenshot_path').value
            },
            vault_document_monitor: {
                enabled: document.getElementById('vault_enabled').checked,
                monitor_interval: parseInt(document.getElementById('vault_interval').value),
                initial_scan: document.getElementById('vault_initial_scan').checked
            }
        }
    };

    try {
        const response = await fetch('/api/settings/general', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        const data = await response.json();

        if (data.code === 0) {
            showToast('截图设置保存成功');
        } else {
            showToast('保存失败: ' + (data.message || '未知错误'), true);
        }
    } catch (error) {
        console.error('保存截图设置失败:', error);
        showToast('保存失败', true);
    }
});

// ==================== 处理配置 ====================

async function loadProcessingSettings() {
    try {
        const response = await fetch('/api/settings/general');
        const data = await response.json();

        if (data.code === 0 && data.data) {
            const proc = data.data.processing || {};

            document.getElementById('doc_enabled').checked = proc.document_processor?.enabled !== false;
            document.getElementById('doc_batch_size').value = proc.document_processor?.batch_size || 10;
            document.getElementById('doc_batch_timeout').value = proc.document_processor?.batch_timeout || 5;

            document.getElementById('screenshot_proc_enabled').checked = proc.screenshot_processor?.enabled !== false;
            document.getElementById('screenshot_batch_size').value = proc.screenshot_processor?.batch_size || 20;
            document.getElementById('screenshot_max_size').value = proc.screenshot_processor?.max_image_size || 1920;

            document.getElementById('merger_enabled').checked = proc.context_merger?.enabled === true;
            document.getElementById('merger_threshold').value = proc.context_merger?.similarity_threshold || 0.9;
        }
    } catch (error) {
        console.error('加载处理设置失败:', error);
        showToast('加载处理设置失败', true);
    }
}

document.getElementById('processingForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const settings = {
        processing: {
            document_processor: {
                enabled: document.getElementById('doc_enabled').checked,
                batch_size: parseInt(document.getElementById('doc_batch_size').value),
                batch_timeout: parseInt(document.getElementById('doc_batch_timeout').value)
            },
            screenshot_processor: {
                enabled: document.getElementById('screenshot_proc_enabled').checked,
                batch_size: parseInt(document.getElementById('screenshot_batch_size').value),
                max_image_size: parseInt(document.getElementById('screenshot_max_size').value)
            },
            context_merger: {
                enabled: document.getElementById('merger_enabled').checked,
                similarity_threshold: parseFloat(document.getElementById('merger_threshold').value)
            }
        }
    };

    try {
        const response = await fetch('/api/settings/general', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        const data = await response.json();

        if (data.code === 0) {
            showToast('处理设置保存成功');
        } else {
            showToast('保存失败: ' + (data.message || '未知错误'), true);
        }
    } catch (error) {
        console.error('保存处理设置失败:', error);
        showToast('保存失败', true);
    }
});

// ==================== 内容生成设置 ====================

async function loadGenerationSettings() {
    try {
        const response = await fetch('/api/settings/general');
        const data = await response.json();

        if (data.code === 0 && data.data) {
            const gen = data.data.content_generation || {};

            document.getElementById('activity_enabled').checked = gen.activity?.enabled !== false;
            document.getElementById('activity_interval').value = gen.activity?.interval || 900;

            document.getElementById('tips_enabled').checked = gen.tips?.enabled !== false;
            document.getElementById('tips_interval').value = gen.tips?.interval || 3600;

            document.getElementById('todos_enabled').checked = gen.todos?.enabled !== false;
            document.getElementById('todos_interval').value = gen.todos?.interval || 1800;

            document.getElementById('report_enabled').checked = gen.report?.enabled !== false;
            document.getElementById('report_time').value = gen.report?.time || '08:00';
        }
    } catch (error) {
        console.error('加载内容生成设置失败:', error);
        showToast('加载内容生成设置失败', true);
    }
}

document.getElementById('generationForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const settings = {
        content_generation: {
            activity: {
                enabled: document.getElementById('activity_enabled').checked,
                interval: parseInt(document.getElementById('activity_interval').value)
            },
            tips: {
                enabled: document.getElementById('tips_enabled').checked,
                interval: parseInt(document.getElementById('tips_interval').value)
            },
            todos: {
                enabled: document.getElementById('todos_enabled').checked,
                interval: parseInt(document.getElementById('todos_interval').value)
            },
            report: {
                enabled: document.getElementById('report_enabled').checked,
                time: document.getElementById('report_time').value
            }
        }
    };

    try {
        const response = await fetch('/api/settings/general', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        const data = await response.json();

        if (data.code === 0) {
            showToast('内容生成设置保存成功');
        } else {
            showToast('保存失败: ' + (data.message || '未知错误'), true);
        }
    } catch (error) {
        console.error('保存内容生成设置失败:', error);
        showToast('保存失败', true);
    }
});

// ==================== Prompts管理 ====================

function buildPromptTree(obj, prefix = '', parentEl = null) {
    const container = parentEl || document.getElementById('promptTree');
    container.innerHTML = '';

    function traverse(obj, prefix) {
        for (const [key, value] of Object.entries(obj)) {
            const fullKey = prefix ? `${prefix}.${key}` : key;

            if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                const hasStringValues = Object.values(value).some(v => typeof v === 'string');

                if (hasStringValues) {
                    // This is a prompt group
                    const groupBtn = document.createElement('button');
                    groupBtn.className = 'list-group-item list-group-item-action fw-bold';
                    groupBtn.textContent = key;
                    groupBtn.onclick = () => {
                        groupBtn.classList.toggle('active');
                        const children = groupBtn.nextElementSibling;
                        children.style.display = children.style.display === 'none' ? 'block' : 'none';
                    };
                    container.appendChild(groupBtn);

                    const childContainer = document.createElement('div');
                    childContainer.style.paddingLeft = '20px';

                    for (const [subKey, subValue] of Object.entries(value)) {
                        if (typeof subValue === 'string') {
                            const btn = document.createElement('button');
                            btn.className = 'list-group-item list-group-item-action';
                            btn.textContent = subKey;
                            btn.onclick = () => selectPrompt(`${fullKey}.${subKey}`);
                            childContainer.appendChild(btn);
                        }
                    }
                    container.appendChild(childContainer);
                } else {
                    // Nested object
                    const groupBtn = document.createElement('button');
                    groupBtn.className = 'list-group-item list-group-item-action text-primary';
                    groupBtn.textContent = key;
                    container.appendChild(groupBtn);

                    const nestedContainer = document.createElement('div');
                    nestedContainer.style.paddingLeft = '15px';
                    container.appendChild(nestedContainer);

                    traverse(value, fullKey, nestedContainer);
                }
            }
        }
    }

    function traverse(obj, prefix, parentEl) {
        for (const [key, value] of Object.entries(obj)) {
            const fullKey = prefix ? `${prefix}.${key}` : key;

            if (typeof value === 'object' && value !== null) {
                const hasStringValues = Object.values(value).some(v => typeof v === 'string');

                if (hasStringValues) {
                    const groupBtn = document.createElement('button');
                    groupBtn.className = 'list-group-item list-group-item-action fw-bold';
                    groupBtn.textContent = key;
                    groupBtn.onclick = function() {
                        this.classList.toggle('active');
                        const children = this.nextElementSibling;
                        if (children) {
                            children.style.display = children.style.display === 'none' ? 'block' : 'none';
                        }
                    };
                    parentEl.appendChild(groupBtn);

                    const childContainer = document.createElement('div');
                    childContainer.style.paddingLeft = '20px';

                    for (const [subKey, subValue] of Object.entries(value)) {
                        if (typeof subValue === 'string') {
                            const btn = document.createElement('button');
                            btn.className = 'list-group-item list-group-item-action';
                            btn.textContent = subKey;
                            btn.onclick = () => selectPrompt(`${fullKey}.${subKey}`);
                            childContainer.appendChild(btn);
                        }
                    }
                    parentEl.appendChild(childContainer);
                }
            }
        }
    }

    traverse(obj, '', container);
}

function getPromptValue(key) {
    const keys = key.split('.');
    let value = currentPrompts;
    for (const k of keys) {
        value = value?.[k];
    }
    return typeof value === 'string' ? value : '';
}

function setPromptValue(key, newValue) {
    const keys = key.split('.');
    let current = currentPrompts;
    for (let i = 0; i < keys.length - 1; i++) {
        current = current[keys[i]];
    }
    current[keys[keys.length - 1]] = newValue;
}

function selectPrompt(key) {
    selectedPromptKey = key;
    document.getElementById('currentPromptKey').textContent = key;
    document.getElementById('promptEditor').value = getPromptValue(key);

    // Remove active class from all buttons
    document.querySelectorAll('#promptTree button').forEach(btn => {
        btn.classList.remove('active');
    });
}

document.getElementById('promptEditor')?.addEventListener('change', (e) => {
    if (selectedPromptKey) {
        setPromptValue(selectedPromptKey, e.target.value);
    }
});

async function loadPrompts() {
    try {
        const response = await fetch('/api/settings/prompts');
        const data = await response.json();

        if (data.code === 0 && data.data) {
            currentPrompts = data.data.prompts;
            buildPromptTree(currentPrompts);
        }
    } catch (error) {
        console.error('加载Prompts失败:', error);
        showToast('加载Prompts失败', true);
    }
}

async function savePrompts() {
    try {
        const response = await fetch('/api/settings/prompts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompts: currentPrompts })
        });
        const data = await response.json();

        if (data.code === 0) {
            showToast('Prompts保存成功');
        } else {
            showToast('保存失败: ' + (data.message || '未知错误'), true);
        }
    } catch (error) {
        console.error('保存Prompts失败:', error);
        showToast('保存失败', true);
    }
}

async function exportPrompts() {
    try {
        const response = await fetch('/api/settings/prompts/export');
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `prompts_${new Date().getTime()}.yaml`;
        a.click();
        window.URL.revokeObjectURL(url);
        showToast('导出成功');
    } catch (error) {
        console.error('导出Prompts失败:', error);
        showToast('导出失败', true);
    }
}

async function importPrompts(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/settings/prompts/import', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        if (data.code === 0) {
            showToast('导入成功');
            loadPrompts();
        } else {
            showToast('导入失败: ' + (data.message || '未知错误'), true);
        }
    } catch (error) {
        console.error('导入Prompts失败:', error);
        showToast('导入失败', true);
    } finally {
        event.target.value = '';
    }
}

async function resetAllSettings() {
    if (!confirm('确认要重置所有设置吗？这将删除所有自定义配置和Prompts，恢复到默认设置。此操作不可撤销！')) {
        return;
    }

    try {
        const response = await fetch('/api/settings/reset', {
            method: 'POST'
        });
        const data = await response.json();

        if (data.code === 0) {
            showToast('设置重置成功，请刷新页面');
            setTimeout(() => location.reload(), 2000);
        } else {
            showToast('重置失败: ' + (data.message || '未知错误'), true);
        }
    } catch (error) {
        console.error('重置设置失败:', error);
        showToast('重置失败', true);
    }
}

// ==================== 模型配置 ====================

async function loadModelSettings() {
    try {
        const response = await fetch('/api/model_settings/get');
        const data = await response.json();

        if (data.code === 0 && data.data && data.data.config) {
            const config = data.data.config;

            // Fill VLM configuration
            document.getElementById('modelPlatform').value = config.modelPlatform || '';
            document.getElementById('modelId').value = config.modelId || '';
            document.getElementById('baseUrl').value = config.baseUrl || '';
            document.getElementById('apiKey').value = config.apiKey || '';

            // Fill Embedding configuration
            document.getElementById('embeddingModelId').value = config.embeddingModelId || '';

            // Check if using separate embedding configuration
            const hasSeparateConfig = config.embeddingBaseUrl || config.embeddingApiKey || config.embeddingModelPlatform;

            if (hasSeparateConfig) {
                document.getElementById('separateEmbedding').checked = true;
                document.getElementById('embeddingModelPlatform').value = config.embeddingModelPlatform || '';
                document.getElementById('embeddingBaseUrl').value = config.embeddingBaseUrl || '';
                document.getElementById('embeddingApiKey').value = config.embeddingApiKey || '';
                toggleEmbeddingConfig();
            }
        }
    } catch (error) {
        console.error('加载模型设置失败:', error);
        showToast('加载模型设置失败', true);
    }
}

function toggleEmbeddingConfig() {
    const checkbox = document.getElementById('separateEmbedding');
    const section = document.getElementById('embeddingConfigSection');
    section.style.display = checkbox.checked ? 'block' : 'none';
}

async function validateModelConfig() {
    try {
        showToast('正在测试连接...', false);

        // Collect current configuration from the form
        const useSeparate = document.getElementById('separateEmbedding').checked;

        const settings = {
            config: {
                modelPlatform: document.getElementById('modelPlatform').value,
                modelId: document.getElementById('modelId').value,
                baseUrl: document.getElementById('baseUrl').value,
                apiKey: document.getElementById('apiKey').value,
                embeddingModelId: document.getElementById('embeddingModelId').value,
                embeddingBaseUrl: useSeparate ? document.getElementById('embeddingBaseUrl').value : null,
                embeddingApiKey: useSeparate ? document.getElementById('embeddingApiKey').value : null,
                embeddingModelPlatform: useSeparate ? document.getElementById('embeddingModelPlatform').value : null
            }
        };

        const response = await fetch('/api/model_settings/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        const data = await response.json();

        if (data.code === 0) {
            showToast('连接测试成功！VLM和Embedding模型均正常');
        } else {
            showToast('连接测试失败: ' + (data.message || '未知错误'), true);
        }
    } catch (error) {
        console.error('模型配置测试失败:', error);
        showToast('连接测试失败', true);
    }
}

document.getElementById('modelForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const useSeparate = document.getElementById('separateEmbedding').checked;

    const settings = {
        config: {
            modelPlatform: document.getElementById('modelPlatform').value,
            modelId: document.getElementById('modelId').value,
            baseUrl: document.getElementById('baseUrl').value,
            apiKey: document.getElementById('apiKey').value,
            embeddingModelId: document.getElementById('embeddingModelId').value,
            embeddingBaseUrl: useSeparate ? document.getElementById('embeddingBaseUrl').value : null,
            embeddingApiKey: useSeparate ? document.getElementById('embeddingApiKey').value : null,
            embeddingModelPlatform: useSeparate ? document.getElementById('embeddingModelPlatform').value : null
        }
    };

    try {
        const response = await fetch('/api/model_settings/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        const data = await response.json();

        if (data.code === 0) {
            showToast('模型配置保存成功');
        } else {
            showToast('保存失败: ' + (data.message || '未知错误'), true);
        }
    } catch (error) {
        console.error('保存模型设置失败:', error);
        showToast('保存失败', true);
    }
});

// ==================== 页面初始化 ====================

document.addEventListener('DOMContentLoaded', function() {
    loadModelSettings();
    loadCaptureSettings();
    loadProcessingSettings();
    loadGenerationSettings();
    loadPromptsToCategories();  // 使用新的加载函数

    // Tab切换时加载对应设置
    document.querySelectorAll('button[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(e) {
            const target = e.target.getAttribute('data-bs-target');
            if (target === '#prompts' && Object.keys(currentPrompts).length === 0) {
                loadPromptsToCategories();  // 使用新的加载函数
            }
        });
    });
});

// ==================== 新的Prompts管理功能 ====================

// Prompt分类映射
const PROMPT_CATEGORIES = {
    'smart_tip_generation': {
        path: 'generation.smart_tip_generation',
        prefix: 'tips'
    },
    'todo_extraction': {
        path: 'generation.todo_extraction',
        prefix: 'todos'
    },
    'generation_report': {
        path: 'generation.generation_report',
        prefix: 'report'
    },
    'realtime_activity_monitor': {
        path: 'generation.realtime_activity_monitor',
        prefix: 'activity'
    }
};

// 当前选中的历史记录
let selectedHistoryFile = null;
let currentCategory = null;

// 加载Prompts时填充到各个分类
async function loadPromptsToCategories() {
    try {
        const [promptsResponse, settingsResponse] = await Promise.all([
            fetch('/api/settings/prompts'),
            fetch('/api/settings/general')
        ]);

        const promptsData = await promptsResponse.json();
        const settingsData = await settingsResponse.json();

        if (promptsData.code === 0 && promptsData.data) {
            // API returns {data: {prompts: {...}}}
            currentPrompts = promptsData.data.prompts || promptsData.data;

            // 填充各个分类的prompts
            for (const [category, config] of Object.entries(PROMPT_CATEGORIES)) {
                const pathParts = config.path.split('.');
                let promptData = currentPrompts;

                for (const part of pathParts) {
                    promptData = promptData?.[part];
                }

                if (promptData) {
                    const systemEl = document.getElementById(`${config.prefix}_system`);
                    const userEl = document.getElementById(`${config.prefix}_user`);

                    if (systemEl) systemEl.value = promptData.system || '';
                    if (userEl) userEl.value = promptData.user || '';
                } else {
                    console.warn(`No prompt data found for category: ${category}, path: ${config.path}`);
                }
            }
        } else {
            console.error('Failed to load prompts:', promptsData);
            showToast('加载Prompts失败: ' + (promptsData.message || '未知错误'), true);
        }

        // 加载Debug配置 from general settings
        if (settingsData.code === 0 && settingsData.data) {
            const debugConfig = settingsData.data.content_generation?.debug || {};
            const debugEnabledEl = document.getElementById('debugEnabled');
            const debugPathEl = document.getElementById('debugOutputPath');

            if (debugEnabledEl) debugEnabledEl.checked = debugConfig.enabled || false;
            if (debugPathEl) {
                // Use resolved path if available, otherwise use the original path
                const outputPath = debugConfig.output_path_resolved || debugConfig.output_path || '';
                debugPathEl.value = outputPath;
            }
        }
    } catch (error) {
        console.error('加载Prompts失败:', error);
        showToast('加载Prompts失败: ' + error.message, true);
    }
}

// 保存单个Prompt分类
async function savePromptCategory(category) {
    const config = PROMPT_CATEGORIES[category];
    if (!config) return;

    const systemPrompt = document.getElementById(`${config.prefix}_system`).value;
    const userPrompt = document.getElementById(`${config.prefix}_user`).value;

    // 更新currentPrompts
    const pathParts = config.path.split('.');
    let target = currentPrompts;

    for (let i = 0; i < pathParts.length - 1; i++) {
        if (!target[pathParts[i]]) target[pathParts[i]] = {};
        target = target[pathParts[i]];
    }

    const lastKey = pathParts[pathParts.length - 1];
    target[lastKey] = {
        system: systemPrompt,
        user: userPrompt
    };

    try {
        const response = await fetch('/api/settings/prompts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompts: currentPrompts })
        });

        const data = await response.json();
        if (data.code === 0) {
            showToast(`${category} 保存成功`);
        } else {
            showToast('保存失败: ' + (data.message || '未知错误'), true);
        }
    } catch (error) {
        console.error('保存Prompt失败:', error);
        showToast('保存失败', true);
    }
}

// 保存全部Prompts
async function saveAllPrompts() {
    // 收集所有分类的prompts
    for (const [category, config] of Object.entries(PROMPT_CATEGORIES)) {
        const systemPrompt = document.getElementById(`${config.prefix}_system`).value;
        const userPrompt = document.getElementById(`${config.prefix}_user`).value;

        const pathParts = config.path.split('.');
        let target = currentPrompts;

        for (let i = 0; i < pathParts.length - 1; i++) {
            if (!target[pathParts[i]]) target[pathParts[i]] = {};
            target = target[pathParts[i]];
        }

        const lastKey = pathParts[pathParts.length - 1];
        target[lastKey] = {
            system: systemPrompt,
            user: userPrompt
        };
    }

    try {
        const response = await fetch('/api/settings/prompts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompts: currentPrompts })
        });

        const data = await response.json();
        if (data.code === 0) {
            showToast('全部Prompts保存成功');
        } else {
            showToast('保存失败: ' + (data.message || '未知错误'), true);
        }
    } catch (error) {
        console.error('保存Prompts失败:', error);
        showToast('保存失败', true);
    }
}

// 保存Debug配置
async function saveDebugConfig() {
    const enabled = document.getElementById('debugEnabled').checked;
    const outputPath = document.getElementById('debugOutputPath').value;

    if (!currentPrompts.content_generation) {
        currentPrompts.content_generation = {};
    }

    currentPrompts.content_generation.debug = {
        enabled: enabled,
        output_path: outputPath
    };

    try {
        const response = await fetch('/api/settings/general', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                content_generation: currentPrompts.content_generation
            })
        });

        const data = await response.json();
        if (data.code === 0) {
            showToast('Debug配置保存成功');
        } else {
            showToast('保存失败: ' + (data.message || '未知错误'), true);
        }
    } catch (error) {
        console.error('保存Debug配置失败:', error);
        showToast('保存失败', true);
    }
}

// 查看历史记录
async function viewHistory(category) {
    currentCategory = category;
    selectedHistoryFile = null;

    document.getElementById('historyCategory').textContent = category;
    document.getElementById('historyDetail').innerHTML = '<p class="text-muted">加载中...</p>';
    document.getElementById('regenerateBtn').disabled = true;
    document.getElementById('exportBtn').disabled = true;
    document.getElementById('compareBtn').disabled = true;

    try {
        const response = await fetch(`/api/settings/prompts/history/${category}`);
        const data = await response.json();

        if (data.code === 0 && data.data) {
            const historyList = document.getElementById('historyList');
            historyList.innerHTML = '';

            if (data.data.length === 0) {
                historyList.innerHTML = '<p class="text-muted">暂无历史记录</p>';
            } else {
                data.data.forEach(item => {
                    const btn = document.createElement('button');
                    btn.className = 'list-group-item list-group-item-action';
                    btn.innerHTML = `
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">${new Date(item.timestamp).toLocaleString()}</h6>
                            <small>${item.has_result ? '✓' : '×'}</small>
                        </div>
                        <small class="text-muted">${item.filename}</small>
                    `;
                    btn.onclick = () => loadHistoryDetail(category, item.filename);
                    historyList.appendChild(btn);
                });
            }

            document.getElementById('historyDetail').innerHTML = '<p class="text-muted">请选择一条历史记录</p>';
        } else {
            showToast('加载历史记录失败', true);
        }
    } catch (error) {
        console.error('加载历史记录失败:', error);
        showToast('加载历史记录失败', true);
    }

    // 显示modal
    const modal = new bootstrap.Modal(document.getElementById('historyModal'));
    modal.show();
}

// 加载历史记录详情
async function loadHistoryDetail(category, filename) {
    selectedHistoryFile = filename;

    try {
        const response = await fetch(`/api/settings/prompts/history/${category}/${filename}`);
        const data = await response.json();

        if (data.code === 0 && data.data) {
            const detail = document.getElementById('historyDetail');

            // 格式化显示Response - 如果是JSON则美化，否则直接显示
            let formattedResponse = '';
            try {
                // 尝试解析为JSON
                const responseObj = typeof data.data.response === 'string'
                    ? JSON.parse(data.data.response)
                    : data.data.response;
                formattedResponse = JSON.stringify(responseObj, null, 2);
            } catch (e) {
                // 不是JSON，直接显示原文
                formattedResponse = data.data.response || '';
            }

            detail.innerHTML = `
                <div class="mb-3">
                    <strong>文件名:</strong> ${filename}
                </div>
                <div class="mb-3">
                    <strong>时间戳:</strong> ${data.data.timestamp || 'N/A'}
                </div>
                <div class="mb-3">
                    <strong>Messages:</strong>
                    <div class="border p-2 bg-light" style="max-height: 200px; overflow-y: auto; white-space: pre-wrap; word-wrap: break-word; font-family: monospace; font-size: 0.875rem;" contenteditable="true">${JSON.stringify(data.data.messages, null, 2)}</div>
                    <small class="text-muted">可编辑（仅用于查看，不会保存）</small>
                </div>
                <div class="mb-3">
                    <strong>Response:</strong>
                    <div class="border p-2 bg-light" style="max-height: 300px; overflow-y: auto; white-space: pre-wrap; word-wrap: break-word; font-family: monospace; font-size: 0.875rem;" contenteditable="true">${formattedResponse}</div>
                    <small class="text-muted">可编辑（仅用于查看，不会保存）</small>
                </div>
            `;

            document.getElementById('regenerateBtn').disabled = false;
            document.getElementById('exportBtn').disabled = false;
            document.getElementById('compareBtn').disabled = true;
        }
    } catch (error) {
        console.error('加载历史记录详情失败:', error);
        showToast('加载详情失败', true);
    }
}

// 使用当前Prompt重新生成
async function regenerateWithCurrent() {
    if (!selectedHistoryFile || !currentCategory) return;

    const config = PROMPT_CATEGORIES[currentCategory];
    if (!config) return;

    const systemPrompt = document.getElementById(`${config.prefix}_system`).value;
    const userPrompt = document.getElementById(`${config.prefix}_user`).value;

    const regenerateBtn = document.getElementById('regenerateBtn');
    const compareBtn = document.getElementById('compareBtn');
    const originalBtnText = regenerateBtn.innerHTML;

    try {
        // 显示加载状态
        regenerateBtn.disabled = true;
        regenerateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>生成中...';
        showToast('正在重新生成，请稍候...', false);

        const response = await fetch('/api/settings/prompts/regenerate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                category: currentCategory,
                history_file: selectedHistoryFile,
                custom_prompts: {
                    system: systemPrompt,
                    user: userPrompt
                }
            })
        });

        const data = await response.json();

        if (data.code === 0) {
            showToast('重新生成成功！');
            // 保存结果用于对比
            window.regeneratedResult = data.data;

            // 启用对比按钮
            compareBtn.disabled = false;

            // 自动打开对比Modal
            setTimeout(() => {
                compareResults();
            }, 500);
        } else {
            showToast('重新生成失败: ' + (data.message || '未知错误'), true);
        }
    } catch (error) {
        console.error('重新生成失败:', error);
        showToast('重新生成失败: ' + error.message, true);
    } finally {
        // 恢复按钮状态
        regenerateBtn.disabled = false;
        regenerateBtn.innerHTML = originalBtnText;
    }
}

// 对比结果
function compareResults() {
    if (!window.regeneratedResult) {
        showToast('请先重新生成', true);
        return;
    }

    const originalResultEl = document.getElementById('originalResult');
    const newResultEl = document.getElementById('newResult');

    // 格式化函数 - 智能判断是否为JSON
    const formatResult = (result) => {
        try {
            // 如果是字符串，尝试解析为JSON
            if (typeof result === 'string') {
                const parsed = JSON.parse(result);
                return JSON.stringify(parsed, null, 2);
            }
            // 如果已经是对象，直接格式化
            return JSON.stringify(result, null, 2);
        } catch (e) {
            // 不是JSON，直接返回原文
            return typeof result === 'string' ? result : String(result);
        }
    };

    // 格式化并显示结果，支持自动换行
    originalResultEl.textContent = formatResult(window.regeneratedResult.original_result);
    newResultEl.textContent = formatResult(window.regeneratedResult.new_result);

    // 添加样式以支持自动换行
    originalResultEl.style.whiteSpace = 'pre-wrap';
    originalResultEl.style.wordWrap = 'break-word';
    newResultEl.style.whiteSpace = 'pre-wrap';
    newResultEl.style.wordWrap = 'break-word';

    const modal = new bootstrap.Modal(document.getElementById('compareModal'));
    modal.show();
}


// 覆盖原有的loadPrompts函数
const originalLoadPrompts = loadPrompts;
loadPrompts = loadPromptsToCategories;

// ==================== Prompt 语言切换 ====================

// 获取当前Prompt语言
async function getCurrentPromptLanguage() {
    try {
        const response = await fetch('/api/settings/prompts/language');
        const data = await response.json();
        if (data.code === 0 && data.data) {
            return data.data.language || 'zh';
        }
    } catch (error) {
        console.error('获取Prompt语言失败:', error);
    }
    return 'zh'; // 默认中文
}

// 切换Prompt语言
async function changePromptLanguage() {
    const language = document.getElementById('promptLanguage').value;

    if (!confirm(`确认切换到${language === 'zh' ? '中文' : '英文'}版本的Prompts吗？当前未保存的修改将丢失。`)) {
        // 用户取消，恢复选择
        const currentLang = await getCurrentPromptLanguage();
        document.getElementById('promptLanguage').value = currentLang;
        return;
    }

    try {
        const response = await fetch('/api/settings/prompts/language', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ language: language })
        });

        const data = await response.json();
        if (data.code === 0) {
            showToast(`已切换到${language === 'zh' ? '中文' : '英文'}版本`);
            // 重新加载Prompts
            await loadPromptsToCategories();
        } else {
            showToast('切换语言失败: ' + (data.message || '未知错误'), true);
        }
    } catch (error) {
        console.error('切换Prompt语言失败:', error);
        showToast('切换语言失败', true);
    }
}

// 页面加载时设置当前语言
document.addEventListener('DOMContentLoaded', async function() {
    const currentLang = await getCurrentPromptLanguage();
    const langSelect = document.getElementById('promptLanguage');
    if (langSelect) {
        langSelect.value = currentLang;
    }
});
