// 消息类型枚举
export enum MessageTypeEnum {
    // 捕获相关
    CAPTURE_CONTEXT = 'CAPTURE_CONTEXT',
    PAGE_CONTENT_UPDATED = 'PAGE_CONTENT_UPDATED',

    // 截图实现放在 popup 即可, 需要考虑实现
    CAPTURE_SCREENSHOT = 'CAPTURE_SCREENSHOT',

    GET_STATE = 'GET_STATE',

    ANALYZE_PAGE_TYPE = 'ANALYZE_PAGE_TYPE',

    GET_METADATA = 'GET_METADATA',

    UPDATE_STATE = 'UPDATE_SETTINGS',
}

export type MessageType = keyof typeof MessageTypeEnum;

// 消息数据接口
export interface MessageData {
    mode?: CaptureMode;
    isActive?: boolean;
    settings?: any;
    contexts?: any[];
    url?: string;
    content?: any;
    [key: string]: any;
}



// 统一消息接口
export interface Message {
    type: MessageType;
    data: MessageData;
}

// 消息响应接口
export interface MessageResponse {
    success: boolean;
    data?: any;
    error?: string;
}

// 消息目标类型
export enum MessageTarget {
    BACKGROUND = 'background',
    CONTENT_SCRIPT = 'content_script',
    POPUP = 'popup',
    ACTIVE_TAB = 'ACTIVE_TAB',
    ALL_TABS = 'ALL_TABS'
}

// 消息传递选项
export interface MessageOptions {
    target: MessageTarget;
    tabId?: number;
    timeout?: number;
}

// 捕获模式类型
export type CaptureMode = 'smart' | 'basic';

// 捕获上下文数据
export interface CaptureContext {
    url: string;
    title: string;
    content: string;
    mode: CaptureMode;
    timestamp: number;
    metadata?: {
        wordCount?: number;
        elementCount?: number;
        imageCount?: number;
    };
}