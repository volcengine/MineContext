import { PopupManager } from './popupManager';

let popupManager: PopupManager | null = null;

console.log("log popupManager");
/**
 * 初始化popup应用
 */
async function initializePopup(): Promise<void> {
    try {
        // 创建popup管理器实例
        popupManager = new PopupManager();

        // 等待初始化完成
        const waitForInit = (): Promise<void> => {
            return new Promise((resolve) => {
                const checkReady = () => {
                    if (popupManager && popupManager.isReady()) {
                        resolve();
                    } else {
                        setTimeout(checkReady, 100);
                    }
                };
                checkReady();
            });
        };

        await waitForInit();
        console.log('Popup application initialized successfully');
    } catch (error) {
        console.error('Failed to initialize popup application:', error);
    }
}

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializePopup);
} else {
    initializePopup();
}

// 导出popup管理器供外部使用（如测试）
export { popupManager };