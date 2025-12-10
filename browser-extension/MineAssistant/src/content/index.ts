import { initializePopupManager } from '../popup/popupManager';
import { initializeApiClient } from '../services/core/apiClient';
import { initializeStorage } from '../storage';

// 初始化状态跟踪
const initializationState = {
    storage: false,
    apiClient: false,
    popupManager: false,
    allComplete: false
};


// 初始化队列 - 按顺序定义初始化函数
const initQueue = [
    initializeStorage,
    initializeApiClient,
    initializePopupManager
];

// 执行初始化队列
async function executeInitQueue(queue: Array<() => Promise<any>>): Promise<void> {
    for (const [index, initFunction] of queue.entries()) {
        const stepName = initFunction.name || `step_${index + 1}`;
        try {
            console.log(`[Initialization] Executing ${stepName} (${index + 1}/${queue.length})`);
            await initFunction();
            console.log(`[Initialization] Completed ${stepName}`);
        } catch (error) {
            console.error(`[Initialization] Failed to execute ${stepName}:`, error);
            console.log(`[Initialization] Continuing with remaining initialization steps...`);
        }
    }
}

async function main() {
    try {
        console.log('[Initialization] Starting main initialization sequence with queue...');

        await executeInitQueue(initQueue);

        initializationState.allComplete = true;
        console.log('[Initialization] All components initialized successfully!');
    } catch (error) {
        console.error('[Initialization] Main initialization sequence failed:', error);
    }
}


main();

export { initializationState };

