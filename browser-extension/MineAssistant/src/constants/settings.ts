import { ExtensionSettings, ExtensionState } from "../types";


// 默认设置
export const DEFAULT_SETTINGS: ExtensionSettings = {
    autoCapture: true,
    captureInterval: 30000, // 30秒
    maxContexts: 100,
    syncEnabled: true,
    backendUrl: 'http://localhost:1733'
} as const;

// 默认状态
export const DEFAULT_STATE: ExtensionState = {
    isActive: false,
    currentUrl: '',
    contextCount: 0,
    settings: DEFAULT_SETTINGS
} as const;
