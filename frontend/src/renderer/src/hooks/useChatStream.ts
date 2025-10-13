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

  // 清理函数
  useEffect(() => {
    return () => {
      chatStreamService.abortStream()
    }
  }, [])

  // 发送消息
  const sendMessage = useCallback(
    async (query: string, context?: ChatStreamRequest['context']) => {
      if (!query.trim() || chatState.isLoading) return

      // 添加用户消息
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

      // 清除之前的流式消息
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

  // 处理流式事件
  const handleStreamEvent = useCallback((event: StreamEvent) => {
    console.log('🎯 处理流式事件:', event.type, event)

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
        console.log('🤔 处理思考/运行事件:', event.type, event.content)
        setChatState((prev) => ({
          ...prev,
          currentStage: event.stage,
          progress: event.progress
        }))

        // 更新或创建流式消息显示思考过程
        // 但不要覆盖已有的内容，而是追加
        setStreamingMessage((prev) => {
          if (prev && prev.stage === event.stage) {
            // 如果是同一阶段，更新内容
            return {
              ...prev,
              content: event.content,
              progress: event.progress,
              timestamp: event.timestamp
            }
          } else {
            // 创建新的思考消息
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
        console.log('📝 处理stream_chunk:', event.content)
        // 处理流式内容块
        if (!currentStreamingId.current) {
          currentStreamingId.current = 'stream_' + Date.now()
          console.log('🆕 创建新的流式消息:', currentStreamingId.current)
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
          console.log('📝 追加到现有流式消息')
          setStreamingMessage((prev) => {
            if (prev) {
              console.log('📝 当前内容长度:', prev.content.length, '新增内容:', event.content)
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
        console.log('✅ 收到完成事件，内容:', event.content)
        // 完成流式传输，将消息添加到历史记录

        // 如果事件本身包含内容，直接使用事件内容
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
          // 否则使用流式消息的内容
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
              // 如果没有有效内容，至少要更新状态
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

  // 处理流式错误
  const handleStreamError = useCallback((error: Error) => {
    console.error('❌ 流式请求错误:', error)

    let errorMessage = error.message
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      errorMessage = '无法连接到AI服务，请检查网络连接和服务状态'
    } else if (error.name === 'AbortError') {
      errorMessage = '请求已取消'
    }

    setChatState((prev) => ({
      ...prev,
      error: errorMessage,
      isLoading: false
    }))
    setStreamingMessage(null)
    currentStreamingId.current = null
  }, [])

  // 处理流式完成
  const handleStreamComplete = useCallback(() => {
    console.log('Stream completed')
    setChatState((prev) => ({
      ...prev,
      isLoading: false
    }))
  }, [])

  // 清空聊天记录
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

  // 停止当前流式请求
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
