import { BrowserContextExtractor } from "./BrowserContextExtractor";
import { BrowserContext, MessageTypeEnum } from "../types";
import browser from 'webextension-polyfill';

/**
 * 内容脚本主类
 * 负责与页面交互，捕获上下文内容
 */
class ContentScript {
    private extractor: BrowserContextExtractor;
    private isActive: boolean = false;
    private observer: MutationObserver | null = null;

    constructor() {
        this.extractor = new BrowserContextExtractor();
    }

    /**
     * 初始化内容脚本
     */
    async init() {
        try {
            await this.initMessageListener();
            // await this.initObserver();
            this.isActive = true;
            console.log('MineAssistant Content Script initialized successfully');
        } catch (error) {
            console.error('Failed to initialize content script:', error);
        }
    }

    /**
     * 初始化消息监听器
     */
    private async initMessageListener() {
        // 添加消息监听器
        browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
            this.handleMessage(message, sender, sendResponse);
            return true; // 保持异步响应
        });
    }

    /**
     * 处理接收到的消息
     */

    private async handleMessage(message: any, sender: browser.Runtime.MessageSender, sendResponse: (response?: any) => void) {
        console.log('Received message:', message);
        try {
            switch (message.type) {
                case MessageTypeEnum.CAPTURE_CONTEXT:
                    const context = await this.captureContext(message.data?.mode || 'smart');
                    sendResponse({ success: true, context });
                    break;
                case MessageTypeEnum.GET_STATE:
                    sendResponse({ success: true, active: this.isActive });
                    break;
                case MessageTypeEnum.ANALYZE_PAGE_TYPE:
                    const _context = await this.extractor.extractContext();
                    sendResponse({ success: true, pageType: _context.metadata.contentType });
                    break;
                case MessageTypeEnum.GET_METADATA:
                    const metadata = await this.getMetadata();
                    sendResponse({ success: true, metadata });
                    break;
                default:
                    sendResponse({ success: false, error: 'Unknown message type' });
            }
        } catch (error) {
            console.error('Error handling message:', error);
            sendResponse({ success: false, error: error instanceof Error ? error.message : 'Unknown error' });
        }
    }

    /**
     * 初始化页面变化观察器
     * todo: 实现页面变化观察器的逻辑
     */
    private async initObserver() {
        // 监听页面变化
        this.observer = new MutationObserver((mutations) => {
            if (this.isActive) {
                this.handlePageChange(mutations);
            }
        });

        this.observer.observe(document.body, {
            childList: true,
            subtree: true,
            characterData: true,
            attributes: true
        });
    }

    /**
     * 处理页面变化
     */
    private async handlePageChange(mutations: MutationRecord[]) {
        // 检查是否有实质性变化
        const hasSignificantChange = mutations.some(mutation => {
            // 检查是否是内容变化
            if (mutation.type === 'characterData' || mutation.type === 'childList') {
                return true;
            }

            // 检查是否是重要属性变化
            if (mutation.type === 'attributes') {
                const importantAttributes = ['title', 'src', 'href', 'content'];
                return importantAttributes.includes(mutation.attributeName || '');
            }

            return false;
        });

        if (hasSignificantChange) {
            console.log('Page content changed, notifying background script');

            // 通知background script页面内容已更新
            browser.runtime.sendMessage({
                type: MessageTypeEnum.PAGE_CONTENT_UPDATED,
                url: location.href,
                title: document.title
            }).catch(error => {
                console.log('Failed to send page update notification:', error);
            });
        }
    }

    /**
     * 捕获上下文
     */
    private async captureContext(mode: 'smart' | 'basic' = 'smart'): Promise<BrowserContext> {
        const contentType = this.extractor.detectContentType();
        if (mode === 'basic') {
            // 基础模式：只提取基本页面信息
            return {
                id: `${location.href}_${Date.now()}`,
                url: location.href,
                title: document.title,
                timestamp: Date.now(),
                metadata: this.extractor.extractMetadata(contentType),
                structuredContent: {
                    title: document.title,
                    contentType: contentType
                }
            };
        }

        // 智能模式：使用完整的内容提取器
        return await this.extractor.extractContext();
    }

    /**
     * 提取内容
     */
    private async extractContent(options?: any): Promise<any> {
        const context = await this.extractor.extractContext();

        // 根据选项过滤内容
        if (options?.contentType) {
            return this.filterContentByType(context, options.contentType);
        }

        return context;
    }

    /**
     * 获取页面元数据
     */
    private async getMetadata(): Promise<any> {
        const context = await this.extractor.extractContext();
        return context.metadata;
    }

    /**
     * 根据类型过滤内容
     */
    private filterContentByType(context: BrowserContext, contentType: string): any {
        switch (contentType) {
            case 'article':
                return context.structuredContent.articleContent;
            case 'code':
                return context.structuredContent.codeContent;
            case 'multimedia':
                return context.structuredContent.multimediaContent;
            case 'data':
                return context.structuredContent.dataContent;
            default:
                return context;
        }
    }

    /**
     * 清理资源
     */
    destroy() {
        if (this.observer) {
            this.observer.disconnect();
            this.observer = null;
        }
        this.isActive = false;
    }
}

// 初始化内容脚本
const contentScript = new ContentScript();
contentScript.init();

// 导出供测试使用
export { ContentScript };