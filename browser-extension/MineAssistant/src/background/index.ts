import browser from "webextension-polyfill";
import { MessageTypeEnum } from "../types";

// 计时器状态
let timerState = {
    isActive: false,
    intervalId: null as number | null,
    captureInterval: 2000, // 默认30秒
    lastCaptureTime: 0
};

browser.runtime.onMessage.addListener((message, sender, sendResponse: (data?: any) => void) => {
    if (message.type === MessageTypeEnum.START_RECODING) {
        // 开始计时
        const { isActive, captureInterval } = message.data || {};
        console.log('start recording', message.data, timerState);
        // 更新计时状态
        timerState.isActive = isActive !== undefined ? isActive : true;

        if (captureInterval) {
            timerState.captureInterval = captureInterval;
        }

        // 清除现有计时器
        if (timerState.intervalId !== null) {
            clearInterval(timerState.intervalId);
            timerState.intervalId = null;
        }

        // 如果需要激活计时器，设置新的计时器
        if (timerState.isActive) {
            console.log(`[Timer] Starting timer with interval: ${timerState.captureInterval}ms`);

            // 设置定时捕获
            timerState.intervalId = setInterval(() => {
                performTimedCapture();
            }, timerState.captureInterval) as unknown as number;
        }

        sendResponse({ success: true, isActive: timerState.isActive });
    }

    if (message.type === MessageTypeEnum.UI_SAVE_SETTINGS) {
        // 更新计时配置
        const { settings } = message.data || {};

        if (settings && settings.captureInterval) {
            timerState.captureInterval = settings.captureInterval;

            // 如果计时器正在运行，重新设置计时器
            if (timerState.isActive && timerState.intervalId !== null) {
                clearInterval(timerState.intervalId);
                timerState.intervalId = setInterval(() => {
                    performTimedCapture();
                }, timerState.captureInterval) as unknown as number;

                console.log(`[Timer] Updated capture interval to: ${timerState.captureInterval}ms`);
            }
        }

        sendResponse({ success: true });
    }

    if (message.type === MessageTypeEnum.ON_TIME_CAPTURE) {
        // 执行定时捕获
        performTimedCapture();
        sendResponse({ success: true });
    }

    return true; // 保持消息通道开放以支持异步响应
});

/**
 * 执行定时捕获
 */
function performTimedCapture(): void {
    console.log('performTimedCapture', timerState, performTimedCapture);
    const now = Date.now();

    // 防止过于频繁的捕获
    if (now - timerState.lastCaptureTime < timerState.captureInterval / 2) {
        console.log('[Timer] Skipping capture - too soon since last capture');
        return;
    }

    timerState.lastCaptureTime = now;

    console.log('[Timer] Performing timed capture');

    // 发送捕获通知到background script
    browser.runtime.sendMessage({
        type: MessageTypeEnum.ON_TIME_CAPTURE,
        data: {
            timestamp: now,
            url: 'test',
            title: 'test title',
        }
    }).catch(error => {
        console.error('[Timer] Failed to send capture notification:', error);
    });
}
