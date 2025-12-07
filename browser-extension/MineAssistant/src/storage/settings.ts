import browser from 'webextension-polyfill';

import { ExtensionSettings, ExtensionState } from "../types";
import { STORAGE_KEYS, DEFAULT_SETTINGS, DEFAULT_STATE } from "../constants";

export class SettingsManager {
    private static instance: SettingsManager;

    static getInstance(): SettingsManager {
        if (!SettingsManager.instance) {
            SettingsManager.instance = new SettingsManager();
        }
        return SettingsManager.instance;
    }

    // 获取设置
    async getSettings(): Promise<ExtensionState> {
        try {
            const result = await browser.storage.local.get(STORAGE_KEYS.SETTINGS);
            const settings = result[STORAGE_KEYS.SETTINGS] as ExtensionState;

            if (!settings) {
                // 如果没有设置，使用默认值
                await this.saveSettings(DEFAULT_STATE);
                return DEFAULT_STATE;
            }

            return settings;
        } catch (error) {
            console.error('Failed to get settings:', error);
            return DEFAULT_STATE;
        }
    }

    // 保存设置
    async saveSettings(settings: ExtensionState): Promise<boolean> {
        try {
            // 验证设置
            const validatedSettings = this.validateSettings(settings);

            await browser.storage.local.set({
                [STORAGE_KEYS.SETTINGS]: validatedSettings
            });

            return true;
        } catch (error) {
            console.error('Failed to save settings:', error);
            return false;
        }
    }

    // 更新部分设置
    async updateSettings(updates: Partial<ExtensionSettings>): Promise<boolean> {
        try {
            const currentSettings = await this.getSettings();
            const newSettings = { ...currentSettings, ...updates };

            return await this.saveSettings(newSettings);
        } catch (error) {
            console.error('Failed to update settings:', error);
            return false;
        }
    }

    // 验证设置 todo: 完善验证逻辑
    // 考虑是否用 react, arco-design 提供的组件,支持控件输入源头的validation
    // 优点: 使用简单
    // 缺点: 体积变大; 重构项目为 react 项目
    private validateSettings(settings: ExtensionState): ExtensionState {
        const validated = { ...settings };

        return validated;
    }

    // 重置为默认设置
    async resetToDefaults(): Promise<boolean> {
        return await this.saveSettings(DEFAULT_STATE);
    }

    // 监听设置变化
    onSettingsChanged(callback: (newSettings: ExtensionSettings) => void): () => void {
        const listener = (changes: { [key: string]: browser.Storage.StorageChange }) => {
            if (changes[STORAGE_KEYS.SETTINGS]) {
                const newSettings = changes[STORAGE_KEYS.SETTINGS].newValue as ExtensionSettings;
                if (newSettings) {
                    callback(newSettings);
                }
            }
        };

        browser.storage.onChanged.addListener(listener);

        // 返回取消监听的函数
        return () => {
            browser.storage.onChanged.removeListener(listener);
        };
    }
}
