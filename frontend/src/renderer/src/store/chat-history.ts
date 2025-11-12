// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import type { ConversationResponse } from '@renderer/services/conversation-service'

// Message type definition
export interface Message {
  id: number
  conversation_id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  updated_at: string
  is_complete: boolean
  status: 'streaming' | 'completed' | 'failed' | 'cancelled'
  metadata?: Record<string, any>
}

// State type definition
export interface ChatHistoryState {
  // Current conversation list
  conversations: ConversationResponse[]
  // Currently active conversation ID
  activeConversationId: number | null
  // Message list for current conversation
  chatHistoryMessages: Message[]
  // Loading state
  loading: boolean
  // Error message
  error: string | null
  // AI assistant visibility for each page
  home: {
    aiAssistantVisible: boolean
  }
  creation: {
    aiAssistantVisible: boolean
  }
}

const initialState: ChatHistoryState = {
  conversations: [],
  activeConversationId: null,
  chatHistoryMessages: [],
  loading: false,
  error: null,
  home: {
    aiAssistantVisible: false
  },
  creation: {
    aiAssistantVisible: false
  }
}

const chatHistorySlice = createSlice({
  name: 'chatHistory',
  initialState,
  reducers: {
    // ========== Conversation List Management ==========

    /**
     * Set conversation list
     */
    setConversations(state, action: PayloadAction<ConversationResponse[]>) {
      state.conversations = action.payload
      state.error = null
    },

    /**
     * Add new conversation to list
     */
    addConversation(state, action: PayloadAction<ConversationResponse>) {
      state.conversations.unshift(action.payload)
      state.error = null
    },

    /**
     * Update conversation information (e.g., title)
     */
    updateConversation(state, action: PayloadAction<{ id: number; updates: Partial<ConversationResponse> }>) {
      const { id, updates } = action.payload
      const index = state.conversations.findIndex((conv) => conv.id === id)
      if (index !== -1) {
        state.conversations[index] = { ...state.conversations[index], ...updates }
      }
      state.error = null
    },

    /**
     * Delete conversation
     */
    deleteConversation(state, action: PayloadAction<number>) {
      state.conversations = state.conversations.filter((conv) => conv.id !== action.payload)
      // Clear active conversation if it's the one being deleted
      if (state.activeConversationId === action.payload) {
        state.activeConversationId = null
        state.chatHistoryMessages = []
      }
      state.error = null
    },

    // ========== Message Management ==========

    /**
     * Set message list for current conversation
     */
    setChatHistoryMessages(state, action: PayloadAction<Message[]>) {
      state.chatHistoryMessages = action.payload
      state.error = null
    },

    /**
     * Add new message
     */
    addMessage(state, action: PayloadAction<Message>) {
      state.chatHistoryMessages.push(action.payload)
      state.error = null
    },

    /**
     * Update message content (for streaming updates)
     */
    updateMessage(state, action: PayloadAction<{ id: number; updates: Partial<Message> }>) {
      const { id, updates } = action.payload
      const index = state.chatHistoryMessages.findIndex((msg) => msg.id === id)
      if (index !== -1) {
        state.chatHistoryMessages[index] = { ...state.chatHistoryMessages[index], ...updates }
      }
      state.error = null
    },

    /**
     * Append message content (for streaming output)
     */
    appendMessageContent(state, action: PayloadAction<{ id: number; content: string }>) {
      const { id, content } = action.payload
      const message = state.chatHistoryMessages.find((msg) => msg.id === id)
      if (message) {
        message.content += content
      }
      state.error = null
    },

    /**
     * Delete message
     */
    deleteMessage(state, action: PayloadAction<number>) {
      state.chatHistoryMessages = state.chatHistoryMessages.filter((msg) => msg.id !== action.payload)
      state.error = null
    },

    /**
     * Clear messages for current conversation
     */
    clearMessages(state) {
      state.chatHistoryMessages = []
      state.error = null
    },

    // ========== Active Conversation Management ==========

    /**
     * Set currently active conversation ID
     */
    setActiveConversationId(state, action: PayloadAction<number | null>) {
      state.activeConversationId = action.payload
      state.error = null
    },

    // ========== UI State Management ==========

    /**
     * Set AI assistant visibility for Home page
     */
    setHomeAiAssistantVisible(state, action: PayloadAction<boolean>) {
      state.home.aiAssistantVisible = action.payload
    },

    /**
     * Set AI assistant visibility for Creation page
     */
    setCreationAiAssistantVisible(state, action: PayloadAction<boolean>) {
      state.creation.aiAssistantVisible = action.payload
    },

    /**
     * Toggle AI assistant visibility for Home page
     */
    toggleHomeAiAssistant(state, action: PayloadAction<boolean>) {
      state.home.aiAssistantVisible = action.payload
    },

    /**
     * Toggle AI assistant visibility for Creation page
     */
    toggleCreationAiAssistant(state, action: PayloadAction<boolean>) {
      state.creation.aiAssistantVisible = action.payload
    },

    // ========== Loading and Error State ==========

    /**
     * Set loading state
     */
    setLoading(state, action: PayloadAction<boolean>) {
      state.loading = action.payload
    },

    /**
     * Set error message
     */
    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload
      state.loading = false
    },

    /**
     * Clear error message
     */
    clearError(state) {
      state.error = null
    },

    /**
     * Reset entire state
     */
    resetChatHistory(state) {
      Object.assign(state, initialState)
    }
  }
})

export const {
  // Conversation list
  setConversations,
  addConversation,
  updateConversation,
  deleteConversation,
  // Message management
  setChatHistoryMessages,
  addMessage,
  updateMessage,
  appendMessageContent,
  deleteMessage,
  clearMessages,
  // Active conversation
  setActiveConversationId,
  // UI state
  setHomeAiAssistantVisible,
  setCreationAiAssistantVisible,
  toggleHomeAiAssistant,
  toggleCreationAiAssistant,
  // Loading and error
  setLoading,
  setError,
  clearError,
  resetChatHistory
} = chatHistorySlice.actions

export default chatHistorySlice.reducer
