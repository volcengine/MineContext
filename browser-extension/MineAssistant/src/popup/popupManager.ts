import browser from 'webextension-polyfill';
import { ExtensionState, ExtensionSettings, MessageTypeEnum } from '../types';
import { DEFAULT_SETTINGS, DEFAULT_STATE } from '../constants';
import storageManager from '../storage';


// TODO:  接入 storage 模块 和 api request 模块,移除多余 state code
export class PopupManager {
    private state: ExtensionState = { ...DEFAULT_STATE };
    private isLoading = false;
    private captureMode: 'smart' | 'basic' = 'smart';
    private isInitialized = false;
    storageManager: any;

    constructor() {
        this.initialize();
    }

    /**
     * 初始化popup管理器
     */
    private async initialize(): Promise<void> {
        console.log("initialize popup manager", browser.storage);
        try {
            // 从存储中加载状态
            this.storageManager = storageManager;
            const savedState = await storageManager.settingsManager.getSettings();

            if (savedState) {
                this.state = {
                    ...DEFAULT_STATE,
                    ...savedState,
                    settings: {
                        ...DEFAULT_SETTINGS,
                        ...savedState.settings
                    }
                };
                console.info("Loaded state:", this.state);
            } else {
                this.state = DEFAULT_STATE;
                console.info("No saved state found, using default state", DEFAULT_STATE);
            }

            this.isInitialized = true;
            this.setupEventListeners();
            this.updateUI();
        } catch (error) {
            console.error('Failed to initialize popup manager:', error);
            this.state = DEFAULT_STATE;
            this.isInitialized = true;
            this.setupEventListeners();
            this.updateUI();
        }
    }

    /**
     * 设置事件监听器
     */
    private setupEventListeners(): void {
        // 开始/停止捕获按钮
        const toggleButton = document.getElementById('toggle-capture-btn') as HTMLButtonElement;
        if (toggleButton) {
            toggleButton.addEventListener('click', this.handleToggleCapture.bind(this));
        }

        // 立即捕获按钮
        const captureButton = document.getElementById('capture-now-btn') as HTMLButtonElement;
        if (captureButton) {
            captureButton.addEventListener('click', this.handleCaptureNow.bind(this));
        }

        // 同步数据按钮
        const syncButton = document.getElementById('sync-data-btn') as HTMLButtonElement;
        if (syncButton) {
            syncButton.addEventListener('click', this.handleSync.bind(this));
        }

        // 自动捕获设置
        const autoCaptureCheckbox = document.getElementById('auto-capture-checkbox') as HTMLInputElement;
        if (autoCaptureCheckbox) {
            autoCaptureCheckbox.addEventListener('change', (e) => {
                const target = e?.target as HTMLInputElement;
                this.updateSettings({ autoCapture: target?.checked || false });
            });
        }

        // 自动同步设置
        const syncEnabledCheckbox = document.getElementById('sync-enabled-checkbox') as HTMLInputElement;
        if (syncEnabledCheckbox) {
            syncEnabledCheckbox.addEventListener('change', (e) => {
                const target = e?.target as HTMLInputElement;
                this.updateSettings({ syncEnabled: target?.checked || false });
            });
        }

        // 捕获间隔设置
        const captureIntervalInput = document.getElementById('capture-interval-input') as HTMLInputElement;
        if (captureIntervalInput) {
            captureIntervalInput.addEventListener('change', (e) => {
                const target = e?.target as HTMLInputElement;
                const value = parseInt(target.value) || 30;

                this.updateSettings({ captureInterval: value * 1000 });
            });
        }

        // 最大存储数量设置
        const maxContextsInput = document.getElementById('max-contexts-input') as HTMLInputElement;
        if (maxContextsInput) {
            maxContextsInput.addEventListener('change', (e) => {
                const target = e?.target as HTMLInputElement;
                const value = parseInt(target.value) || 100;
                this.updateSettings({ maxContexts: value });
            });
        }

        // 后端URL设置
        const backendUrlInput = document.getElementById('backend-url-input') as HTMLInputElement;
        if (backendUrlInput) {
            backendUrlInput.addEventListener('change', (e) => {
                const target = e?.target as HTMLInputElement;
                this.updateSettings({ backendUrl: target.value });
            });
        }

        // 捕获模式设置
        const captureModeSelect = document.getElementById('capture-mode-select') as HTMLSelectElement;
        if (captureModeSelect) {
            captureModeSelect.addEventListener('change', (e) => {
                const target = e?.target as HTMLInputElement;
                this.captureMode = target.value as 'smart' | 'basic';
            });
        }

        // 监听来自background script的消息
        browser.runtime.onMessage.addListener(this.handleMessage.bind(this));
    }

    /**
     * 处理消息
     */
    private handleMessage(message: any, sender: browser.Runtime.MessageSender, sendResponse: (response?: any) => void): true | void | Promise<any> {
        console.log('Received message from background:', message);
        switch (message.type) {
            // 来自 UI 的 action
            case MessageTypeEnum.UI_CAPTURE_NOW:
                const response = this.handleCaptureNow();
                this.updateUI();
                console.log('[MessageTypeEnum.UI_CAPTURE_NOW] response', response)
                sendResponse(response);
                break;
            case MessageTypeEnum.START_RECODING:
                this.state = {
                    ...this.state,
                    contextCount: this.state.contextCount + 1
                };
                this.updateUI();
                sendResponse({ success: true });
                break;
            case MessageTypeEnum.UI_SAVE_SETTINGS:
                this.updateUI();
                sendResponse({ success: true });
                break;

            // 来自 background 的通讯
            case MessageTypeEnum.ON_TIME_CAPTURE:
                this.handleCaptureNow();
                break;
            case MessageTypeEnum.ON_TIME_UPLOAD:
                this.handleSync();
                break;
            default:
                console.warn(`Unhandled message type: ${message.type}`);
        }
    }

    /**
     * 保存状态到存储
     */
    private async saveState(): Promise<void> {
        try {
            await this.storageManager.saveSettings(this.state.settings);
        } catch (error) {
            console.error('Failed to save extension state:', error);
        }
    }

    /**
     * 处理开始/停止捕获
     */
    private async handleToggleCapture(): Promise<void> {
        this.setLoading(true);
        try {
            const newState = {
                ...this.state,
                isActive: !this.state.isActive
            };

            this.saveState();
            this.state = newState;

            // 通知background script
            try {
                browser.runtime.sendMessage({
                    type: MessageTypeEnum.START_RECODING,
                    data: { isActive: this.state.isActive, captureInterval: this.state.settings.captureInterval }
                });
            } catch (error) {
                console.error('Failed to send toggle capture message:', error);
            }

            console.log('handleToggleCapture', this.state);
            this.updateUI();
            this.setLoading(false);

        } finally {
            this.setLoading(false);
        }
    }

    /**
     * 处理立即捕获
     */
    private async handleCaptureNow() {
        console.info("Capturing context now...");

        this.setLoading(true);
        try {
            // 获取当前活动标签页
            const [tab] = await browser.tabs.query({ active: true, currentWindow: true });

            if (tab && tab.id) {
                // 发送捕获消息到content script
                const screenshot = await browser.tabs.captureVisibleTab();
                const response = await browser.tabs.sendMessage(tab.id, {
                    type: 'CAPTURE_CONTEXT',
                    data: { mode: this.captureMode, screenshot }
                });

                console.log('response', response);
                console.log('screenshot', screenshot)

                if (response && response.success) {
                    // 更新上下文计数和当前URL
                    this.state = {
                        ...this.state,
                        contextCount: this.state.contextCount + 1,
                        currentUrl: tab.url || '',
                    };
                }

                return response;
            }
        } catch (error) {
            console.error('Failed to capture context:', error);
        } finally {
            this.setLoading(false);
        }
    }

    /**
     * 处理同步数据
     */
    private async handleSync(): Promise<void> {
        this.setLoading(true);
        try {
            // 获取所有存储的上下文数据
            const result = await browser.storage.local.get(['contexts']);
            const contexts = result.contexts || [];

            if (contexts.length === 0) {
                console.log('No data to sync');
                return;
            }

            // 发送到后端API
            const response = await fetch(`${this.state.settings.backendUrl}/api/contexts/sync`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ contexts })
            });

            if (response.ok) {
                // 更新状态
                this.state = {
                    ...this.state,
                    lastSyncTime: Date.now()
                };
                await this.saveState();
                this.updateUI();
            } else {
                console.error(`Sync failed: ${response.status} ${response.statusText}`);
            }
        } catch (error) {
            console.error('Failed to sync data:', error);
        } finally {
            this.setLoading(false);
        }
    }

    /**
     * 更新设置
     */
    private async updateSettings(newSettings: Partial<ExtensionSettings>) {
        console.log('updateSettings', newSettings);
        const updatedSettings = {
            ...this.state.settings,
            ...newSettings
        };

        this.state = {
            ...this.state,
            settings: updatedSettings
        };

        await this.saveState();

        // 通知background script设置已更新
        try {
            await browser.runtime.sendMessage({
                type: MessageTypeEnum.UI_SAVE_SETTINGS,
                data: { settings: updatedSettings }
            });
        } catch (error) {
            console.error('Failed to send settings update message:', error);
        }

        this.updateUI();
    }

    /**
     * 设置加载状态
     */
    private setLoading(loading: boolean): void {
        this.isLoading = loading;
        this.updateUI();
    }

    /**
     * 更新UI
     */
    private updateUI(): void {
        // 更新状态指示器
        const statusDot = document.querySelector('.status-dot') as HTMLElement;
        const statusText = document.querySelector('.status-text') as HTMLElement;

        if (statusDot && statusText) {
            if (this.state.isActive) {
                statusDot.classList.add('active');
                statusDot.classList.remove('inactive');
                statusText.textContent = '运行中';
            } else {
                statusDot.classList.add('inactive');
                statusDot.classList.remove('active');
                statusText.textContent = '已停止';
            }
        }

        // 更新统计信息
        const contextCountElement = document.querySelector('.stat-value') as HTMLElement;
        if (contextCountElement) {
            contextCountElement.textContent = this.state.contextCount.toString();
        }

        const currentUrlElement = document.querySelector('.stat-url') as HTMLElement;
        if (currentUrlElement) {
            currentUrlElement.textContent = this.state.currentUrl || '无';
        }

        // 更新控制按钮
        const toggleButton = document.getElementById('toggle-capture-btn') as HTMLButtonElement;
        if (toggleButton) {
            toggleButton.textContent = this.state.isActive ? '停止捕获' : '开始捕获';
            toggleButton.className = this.state.isActive ? 'btn btn-stop' : 'btn btn-start';
            toggleButton.disabled = this.isLoading;
        }

        // const captureButton = document.getElementById('capture-now-btn') as HTMLButtonElement;


        // const syncButton = document.getElementById('sync-data-btn') as HTMLButtonElement;
        // if (syncButton) {
        //     syncButton.disabled = this.isLoading;
        // }

        // 更新设置输入框
        const autoCaptureCheckbox = document.getElementById('auto-capture-checkbox') as HTMLInputElement;
        if (autoCaptureCheckbox) {
            autoCaptureCheckbox.checked = this.state.settings.autoCapture;
        }

        const syncEnabledCheckbox = document.getElementById('sync-enabled-checkbox') as HTMLInputElement;
        if (syncEnabledCheckbox) {
            syncEnabledCheckbox.checked = this.state.settings.syncEnabled;
        }

        const captureIntervalInput = document.getElementById('capture-interval-input') as HTMLInputElement;
        if (captureIntervalInput) {
            captureIntervalInput.value = (this.state.settings.captureInterval / 1000).toString();
        }

        const maxContextsInput = document.getElementById('max-contexts-input') as HTMLInputElement;
        if (maxContextsInput) {
            maxContextsInput.value = this.state.settings.maxContexts.toString();
        }

        const backendUrlInput = document.getElementById('backend-url-input') as HTMLInputElement;
        if (backendUrlInput) {
            backendUrlInput.value = this.state.settings.backendUrl;
        }

        const captureModeSelect = document.getElementById('capture-mode-select') as HTMLSelectElement;
        if (captureModeSelect) {
            captureModeSelect.value = this.captureMode;
        }

        // 更新加载状态
        const loadingOverlay = document.querySelector('.loading-overlay') as HTMLElement;
        if (loadingOverlay) {
            loadingOverlay.style.display = this.isLoading ? 'flex' : 'none';
        }
    }

    /**
     * 获取当前状态
     */
    public getState(): ExtensionState {
        return { ...this.state };
    }

    /**
     * 获取是否初始化完成
     */
    public isReady(): boolean {
        return this.isInitialized;
    }
}

let popupManager: PopupManager | null;


export async function initializePopupManager(): Promise<void> {
    try {
        // 创建popup管理器实例
        popupManager = new PopupManager();

        // 等待初始化完成
        const waitForInit = (): Promise<void> => {
            return new Promise((resolve) => {
                const checkReady = () => {
                    if (popupManager && popupManager.isReady()) {
                        resolve();
                    } else {
                        setTimeout(checkReady, 100);
                    }
                };
                checkReady();
            });
        };

        await waitForInit();
        console.log('Popup application initialized successfully', popupManager);
    } catch (error) {
        console.error('Failed to initialize popup application:', error);
    }
}