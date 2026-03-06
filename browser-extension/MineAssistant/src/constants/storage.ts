export const STORAGE_KEYS = {
    SETTINGS: 'MineAssistant_settings',
    CONTEXTS: 'MineAssistant_contexts',
    SYNC_STATE: 'MineAssistant_sync_state',
    LAST_SYNC_TIME: 'MineAssistant_last_sync_time'
} as const;

export const STORAGE_LIMITS = {
    MAX_CONTEXTS: 100,
    MAX_CONTEXT_SIZE: 1024 * 1024, // 1MB
    MAX_TOTAL_SIZE: 5 * 1024 * 1024 // 5MB
}

export const GET_RECENT_CONTEXTS_LIMIT = 10;

export const LOCAL_STORAGE_KEYS = {
    SETTINGS: 'MineAssistant_settings',
    CONTEXTS: 'MineAssistant_contexts',
    SYNC_STATE: 'MineAssistant_sync_state',
    LAST_SYNC_TIME: 'MineAssistant_last_sync_time'
} as const;
