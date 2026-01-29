// 消息类型枚举
export enum MessageTypeEnum {
    //todo: 是否要这么设计 当插件配置 ready 时,发出信号, storage 的插件值允许读取
    // SETTING_READY = 'SETTING_READY',

    // 对应 UI 操作
    UI_START_RECORDING = 'UI_START_RECORDING',
    UI_CAPTURE_NOW = 'UI_CAPTURE_NOW',
    UI_SAVE_SETTINGS = 'UI_SAVE_SETTINGS',

    // 对应 background 后台操作
    START_RECODING = 'START_RECODING',// 开始计时
    ON_TIME_CAPTURE = 'ON_TIME_CAPTURE',
    ON_TIME_UPLOAD = 'ON_TIME_UPLOAD',
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