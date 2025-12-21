import browser from 'webextension-polyfill';

import { BrowserContext } from "../types";
import { GET_RECENT_CONTEXTS_LIMIT, STORAGE_KEYS, STORAGE_LIMITS } from "../constants";

// 上下文存储管理器
// todo 暂时存储再 browser.storage 中
// 后续扩容考虑存储到 IndexedDB 中
export interface ContextStorageOptions {
    maxContexts?: number;
    maxContextSize?: number;
}

export class ContextManager {
    private static instance: ContextManager;
    private options: ContextStorageOptions;

    static getInstance(options: ContextStorageOptions = {}): ContextManager {
        if (!ContextManager.instance) {
            ContextManager.instance = new ContextManager(options);
        }
        return ContextManager.instance;
    }

    private constructor(options: ContextStorageOptions = {}) {
        this.options = {
            maxContexts: options?.maxContexts || STORAGE_LIMITS.MAX_CONTEXTS,
            maxContextSize: options?.maxContextSize || STORAGE_LIMITS.MAX_CONTEXT_SIZE
        };
    }

    // 获取所有上下文
    async getContexts(): Promise<BrowserContext[]> {
        try {
            const result = await browser.storage.local.get(STORAGE_KEYS.CONTEXTS);
            return result[STORAGE_KEYS.CONTEXTS] || [];
        } catch (error) {
            console.error('Failed to get contexts:', error);
            return [];
        }
    }

    // 添加新上下文
    async addContext(context: BrowserContext): Promise<boolean> {
        try {
            // 验证上下文大小
            const contextSize = JSON.stringify(context).length;
            if (contextSize > this.options.maxContextSize!) {
                console.warn('Context size exceeds limit, skipping');
                return false;
            }

            const contexts = await this.getContexts();

            // 检查是否已经存在相同的上下文（基于URL和时间戳）
            const existingIndex = contexts.findIndex(c =>
                c.url === context.url && c.timestamp === context.timestamp
            );

            if (existingIndex !== -1) {
                // 更新现有上下文
                contexts[existingIndex] = context;
            } else {
                // 添加新上下文
                contexts.unshift(context); // 最新的在前面

                // 限制数量
                if (contexts.length > this.options.maxContexts!) {
                    contexts.splice(this.options.maxContexts!);
                }
            }

            await browser.storage.local.set({
                [STORAGE_KEYS.CONTEXTS]: contexts
            });

            return true;
        } catch (error) {
            console.error('Failed to add context:', error);
            return false;
        }
    }

    // 删除上下文
    async removeContext(url: string, timestamp: number): Promise<boolean> {
        try {
            const contexts = await this.getContexts();
            const filteredContexts = contexts.filter(c =>
                !(c.url === url && c.timestamp === timestamp)
            );

            if (filteredContexts.length === contexts.length) {
                return false; // 没有找到要删除的上下文
            }

            await browser.storage.local.set({
                [STORAGE_KEYS.CONTEXTS]: filteredContexts
            });

            return true;
        } catch (error) {
            console.error('Failed to remove context:', error);
            return false;
        }
    }

    async removeContextById(id: string): Promise<boolean> {
        try {
            const contexts = await this.getContexts();
            const filteredContexts = contexts.filter(c =>
                !(c.id === id)
            );

            if (filteredContexts.length === contexts.length) {
                return false; // 没有找到要删除的上下文
            }

            await browser.storage.local.set({
                [STORAGE_KEYS.CONTEXTS]: filteredContexts
            });

            return true;
        } catch (error) {
            console.error('Failed to remove context:', error);
            return false;
        }
    }

    // 清空所有上下文
    async clearContexts(): Promise<boolean> {
        try {
            await browser.storage.local.remove(STORAGE_KEYS.CONTEXTS);
            return true;
        } catch (error) {
            console.error('Failed to clear contexts:', error);
            return false;
        }
    }

    // 获取最近的上下文
    async getRecentContexts(limit: number = GET_RECENT_CONTEXTS_LIMIT): Promise<BrowserContext[]> {
        try {
            const contexts = await this.getContexts();
            return contexts.slice(0, limit);
        } catch (error) {
            console.error('Failed to get recent contexts:', error);
            return [];
        }
    }

    // 按域名获取上下文
    async getContextsByDomain(domain: string): Promise<BrowserContext[]> {
        try {
            const contexts = await this.getContexts();
            return contexts.filter(context => {
                try {
                    const url = new URL(context.url);
                    return url.hostname === domain;
                } catch {
                    return false;
                }
            });
        } catch (error) {
            console.error('Failed to get contexts by domain:', error);
            return [];
        }
    }

    // 获取存储统计信息
    async getStorageStats(): Promise<{
        totalContexts: number;
        totalSize: number;
        oldestContext?: BrowserContext;
        newestContext?: BrowserContext;
    }> {
        try {
            const contexts = await this.getContexts();
            const totalSize = contexts.reduce((size, context) =>
                size + JSON.stringify(context).length, 0
            );

            return {
                totalContexts: contexts.length,
                totalSize,
                oldestContext: contexts.length > 0 ? contexts[contexts.length - 1] : undefined,
                newestContext: contexts.length > 0 ? contexts[0] : undefined
            };
        } catch (error) {
            console.error('Failed to get storage stats:', error);
            return {
                totalContexts: 0,
                totalSize: 0
            };
        }
    }

    // 监听上下文变化
    // perf: 考虑频繁触发时进行防抖, 300ms
    onContextsChanged(callback: (contexts: BrowserContext[]) => void) {
        const listener = (changes: { [key: string]: browser.Storage.StorageChange }) => {
            if (changes[STORAGE_KEYS.CONTEXTS]) {
                const newContexts = changes[STORAGE_KEYS.CONTEXTS].newValue as BrowserContext[];
                if (newContexts) {
                    callback(newContexts);
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