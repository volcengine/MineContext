
import { BrowserContext, ExtensionSettings } from "../types";

import { SettingsManager } from './settings';
import { ContextManager } from './context';

export class StorageManager {
    private static instance: StorageManager;
    private settingsManager: SettingsManager;
    private contextManager: ContextManager;

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

    // 设置管理
    async getSettings(): Promise<ExtensionSettings> {
        return await this.settingsManager.getSettings();
    }

    async saveSettings(settings: ExtensionSettings) {
        return await this.settingsManager.saveSettings(settings);
    }

    // 上下文管理
    async getContexts() {
        return await this.contextManager.getContexts();
    }

    async addContext(context: BrowserContext) {
        return await this.contextManager.addContext(context);
    }

    async removeContextById(contextId: string) {
        return await this.contextManager.removeContextById(contextId);
    }

    async removeContext(url: string, timestamp: number) {
        return await this.contextManager.removeContext(url, timestamp);
    }

    async clearContexts() {
        return await this.contextManager.clearContexts();
    }

    async getRecentContexts(count: number) {
        return await this.contextManager.getRecentContexts(count);
    }
    async getRecentContextsByDomain(domain: string) {
        return await this.contextManager.getContextsByDomain(domain);
    }
}

const storageManager = StorageManager.getInstance();

export default storageManager;
