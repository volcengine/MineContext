
import { BrowserContext, ExtensionState } from "../types";

import { SettingsManager } from './settings';
import { ContextManager } from './context';

export class StorageManager {
    private static instance: StorageManager;
    public settingsManager: SettingsManager;
    private contextManager: ContextManager;
    private isInitialized = false;

    constructor() {
        this.settingsManager = SettingsManager.getInstance();
        this.contextManager = ContextManager.getInstance();
    }

    static getInstance() {
        if (!this.instance) {
            this.instance = new StorageManager();
        }
        return this.instance;
    }

    // 初始化函数 - 确保在使用前完成初始化
    async initialize(): Promise<void> {
        if (this.isInitialized) {
            console.log('[Storage] Already initialized');
            return;
        }

        try {
            console.log('[Storage] Initializing...');

            // 初始化设置管理器
            await this.settingsManager.getSettings();

            // 初始化上下文管理器
            await this.contextManager.getContexts();

            this.isInitialized = true;
            console.log('[Storage] Initialization completed');
        } catch (error) {
            console.error('[Storage] Initialization failed:', error);
            throw error;
        }
    }

    // 检查是否已初始化
    isReady(): boolean {
        return this.isInitialized;
    }

    // 确保已初始化的装饰器
    private ensureInitialized() {
        if (!this.isInitialized) {
            throw new Error('StorageManager is not initialized. Call initialize() first.');
        }
    }

    // 设置管理
    async getSettings(): Promise<ExtensionState> {
        this.ensureInitialized();
        return await this.settingsManager.getSettings();
    }

    async saveSettings(settings: ExtensionState) {
        this.ensureInitialized();
        return await this.settingsManager.saveSettings(settings);
    }

    // 上下文管理
    async getContexts() {
        this.ensureInitialized();
        return await this.contextManager.getContexts();
    }

    async addContext(context: BrowserContext) {
        this.ensureInitialized();
        return await this.contextManager.addContext(context);
    }

    async removeContextById(contextId: string) {
        this.ensureInitialized();
        return await this.contextManager.removeContextById(contextId);
    }

    async removeContext(url: string, timestamp: number) {
        this.ensureInitialized();
        return await this.contextManager.removeContext(url, timestamp);
    }

    async clearContexts() {
        this.ensureInitialized();
        return await this.contextManager.clearContexts();
    }

    async getRecentContexts(count: number) {
        this.ensureInitialized();
        return await this.contextManager.getRecentContexts(count);
    }
    async getRecentContextsByDomain(domain: string) {
        this.ensureInitialized();
        return await this.contextManager.getContextsByDomain(domain);
    }
}

const storageManager = StorageManager.getInstance();

export const initializeStorage = async (): Promise<StorageManager> => {
    await storageManager.initialize();
    return storageManager;
};

// 便捷的获取已初始化实例的方式
let initializedInstance: StorageManager | null = null;

export const getStorageManager = async (): Promise<StorageManager> => {
    if (!initializedInstance) {
        initializedInstance = await initializeStorage();
    }
    return initializedInstance;
};

// 保持向后兼容的默认导出（但不推荐直接使用）
export default storageManager;
