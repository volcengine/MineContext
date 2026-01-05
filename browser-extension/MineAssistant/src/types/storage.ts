import { BrowserContext } from "./";


// 扩展状态类型
export interface ExtensionState {
    isActive: boolean;
    currentUrl: string;
    contextCount: number;
    lastSyncTime?: number;
    settings: ExtensionSettings;
}

export interface ExtensionSettings {
    autoCapture: boolean;
    captureInterval: number;
    maxContexts: number;
    syncEnabled: boolean;
    backendUrl: string;
}

// 存储类型
export interface StorageData {
    contexts: BrowserContext[];
    settings: ExtensionSettings;
    state: ExtensionState;
}