export const STORAGE_KEYS = {
    SETTINGS: 'mineAssistant_settings',
    CONTEXTS: 'mineAssistant_contexts',
    SYNC_STATE: 'mineAssistant_sync_state',
    LAST_SYNC_TIME: 'mineAssistant_last_sync_time'
} as const;

export const STORAGE_LIMITS = {
    MAX_CONTEXTS: 100,
    MAX_CONTEXT_SIZE: 1024 * 1024, // 1MB
    MAX_TOTAL_SIZE: 5 * 1024 * 1024 // 5MB
}

export const GET_RECENT_CONTEXTS_LIMIT = 10;