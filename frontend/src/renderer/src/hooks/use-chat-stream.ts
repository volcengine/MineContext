// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useState, useCallback, useRef, useEffect } from 'react'
import {
  ChatMessage,
  ChatStreamRequest,
  StreamEvent,
  WorkflowStage,
  chatStreamService
} from '@renderer/services/ChatStreamService'

export interface ChatState {
  messages: ChatMessage[]
  isLoading: boolean
  currentStage?: WorkflowStage
  progress: number
  sessionId: string
  error?: string
}

export interface StreamingMessage {
  id: string
  role: 'assistant'
  content: string
  isStreaming: boolean
  stage?: WorkflowStage
  progress: number
  timestamp: string
}

export const useChatStream = () => {
  const [chatState, setChatState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    progress: 0,
    sessionId: chatStreamService.generateSessionId()
  })

  const [streamingMessage, setStreamingMessage] = useState<StreamingMessage | null>(null)
  const currentStreamingId = useRef<string | null>(null)

  // Cleanup function
  useEffect(() => {
    return () => {
      chatStreamService.abortStream()
    }
  }, [])

  // Send message
  const sendMessage = useCallback(
    async (query: string, context?: ChatStreamRequest['context']) => {
      if (!query.trim() || chatState.isLoading) return

      // Add user message
      const userMessage: ChatMessage = {
        role: 'user',
        content: query.trim()
      }

      setChatState((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
        isLoading: true,
        error: undefined
      }))

      // Clear previous streaming message
      setStreamingMessage(null)
      currentStreamingId.current = null

      const request: ChatStreamRequest = {
        query: query.trim(),
        context: {
          ...context,
          chat_history: [...chatState.messages, userMessage]
        },
        session_id: chatState.sessionId
      }

      try {
        await chatStreamService.sendStreamMessage(request, handleStreamEvent, handleStreamError, handleStreamComplete)
      } catch (error) {
        handleStreamError(error as Error)
      }
    },
    [chatState.messages, chatState.isLoading, chatState.sessionId]
  )

  // Handle stream events
  const handleStreamEvent = useCallback((event: StreamEvent) => {
    console.log('🎯 Handling stream event:', event.type, event)

    switch (event.type) {
      case 'session_start':
        if (event.session_id) {
          setChatState((prev) => ({
            ...prev,
            sessionId: event.session_id!
          }))
        }
        break

      case 'thinking':
      case 'running':
        console.log('🤔 Handling thinking/running event:', event.type, event.content)
        setChatState((prev) => ({
          ...prev,
          currentStage: event.stage,
          progress: event.progress
        }))

        // Update or create a streaming message to show the thinking process
        // but append instead of overwriting existing content
        setStreamingMessage((prev) => {
          if (prev && prev.stage === event.stage) {
            // If it's the same stage, update the content
            return {
              ...prev,
              content: event.content,
              progress: event.progress,
              timestamp: event.timestamp
            }
          } else {
            // Create a new thinking message
            return {
              id: 'thinking_' + Date.now(),
              role: 'assistant',
              content: event.content,
              isStreaming: true,
              stage: event.stage,
              progress: event.progress,
              timestamp: event.timestamp
            }
          }
        })
        break

      case 'stream_chunk':
        console.log('📝 Handling stream_chunk:', event.content)
        // Handle streaming content chunk
        if (!currentStreamingId.current) {
          currentStreamingId.current = 'stream_' + Date.now()
          console.log('🆕 Creating new streaming message:', currentStreamingId.current)
          setStreamingMessage({
            id: currentStreamingId.current,
            role: 'assistant',
            content: event.content,
            isStreaming: true,
            stage: event.stage,
            progress: event.progress,
            timestamp: event.timestamp
          })
        } else {
          console.log('📝 Appending to existing streaming message')
          setStreamingMessage((prev) => {
            if (prev) {
              console.log('📝 Current content length:', prev.content.length, 'New content:', event.content)
              return {
                ...prev,
                content: prev.content + event.content,
                progress: event.progress,
                timestamp: event.timestamp
              }
            }
            return null
          })
        }
        break

      case 'stream_complete':
      case 'completed':
        console.log('✅ Received completion event, content:', event.content)
        // Finish streaming, add message to history

        // If the event itself contains content, use it directly
        if (event.content && event.content.trim()) {
          const finalMessage: ChatMessage = {
            role: 'assistant',
            content: event.content
          }

          setChatState((prev) => ({
            ...prev,
            messages: [...prev.messages, finalMessage],
            isLoading: false,
            currentStage: 'completed',
            progress: 1.0
          }))

          setStreamingMessage(null)
          currentStreamingId.current = null
        } else {
          // Otherwise, use the content of the streaming message
          setStreamingMessage((prev) => {
            if (prev && prev.content.trim()) {
              const finalMessage: ChatMessage = {
                role: 'assistant',
                content: prev.content
              }

              setChatState((chatState) => ({
                ...chatState,
                messages: [...chatState.messages, finalMessage],
                isLoading: false,
                currentStage: 'completed',
                progress: 1.0
              }))

              currentStreamingId.current = null
            } else {
              // If there is no valid content, at least update the status
              setChatState((chatState) => ({
                ...chatState,
                isLoading: false,
                currentStage: 'completed',
                progress: 1.0
              }))
            }
            return null
          })
        }
        break

      case 'fail':
        setChatState((prev) => ({
          ...prev,
          error: event.content,
          isLoading: false,
          currentStage: 'failed'
        }))
        setStreamingMessage(null)
        break

      case 'done':
        setChatState((prev) => ({
          ...prev,
          currentStage: event.stage,
          progress: event.progress
        }))
        break
    }
  }, [])

  // Handle stream error
  const handleStreamError = useCallback((error: Error) => {
    console.error('❌ Stream request error:', error)

    let errorMessage = error.message
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      errorMessage = 'Unable to connect to AI service, please check network connection and service status'
    } else if (error.name === 'AbortError') {
      errorMessage = 'Request has been cancelled'
    }

    setChatState((prev) => ({
      ...prev,
      error: errorMessage,
      isLoading: false
    }))
    setStreamingMessage(null)
    currentStreamingId.current = null
  }, [])

  // Handle stream completion
  const handleStreamComplete = useCallback(() => {
    console.log('Stream completed')
    setChatState((prev) => ({
      ...prev,
      isLoading: false
    }))
  }, [])

  // Clear chat history
  const clearChat = useCallback(() => {
    chatStreamService.abortStream()
    setChatState({
      messages: [],
      isLoading: false,
      progress: 0,
      sessionId: chatStreamService.generateSessionId()
    })
    setStreamingMessage(null)
    currentStreamingId.current = null
  }, [])

  // Stop the current streaming request
  const stopStreaming = useCallback(() => {
    chatStreamService.abortStream()
    setChatState((prev) => ({
      ...prev,
      isLoading: false
    }))
    setStreamingMessage(null)
  }, [])

  return {
    ...chatState,
    streamingMessage,
    sendMessage,
    clearChat,
    stopStreaming
  }
}
