// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useCallback, useMemo, FC } from 'react'
import { Button, Input, Typography, Tag } from '@arco-design/web-react'
import { IconStop } from '@arco-design/web-react/icon'
import { useChatStream } from '@renderer/hooks/use-chat-stream'
import { ChatContext } from '@renderer/services/ChatStreamService'
import MarkdownIt from 'markdown-it'
import chatEditIcon from '@renderer/assets/icons/chat-edit.svg'
import chatSendIcon from '@renderer/assets/icons/chat-send.svg'
import { useMemoizedFn, useRequest } from 'ahooks'
import { conversationService } from '@renderer/services/conversation-service'
import { getLogger } from '@shared/logger/renderer'
import { messageService } from '@renderer/services/messages-service'
import { AIAssistantHeader } from './header'

const { Text } = Typography
const { TextArea } = Input
const logger = getLogger('AIAssistant')

// Initialize markdown parser
const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true
})

interface AIAssistantProps {
  visible: boolean
  onClose: () => void
  pageName: string
}

// Markdown rendering component
export const MarkdownContent: React.FC<{ content: string }> = ({ content }) => {
  const htmlContent = useMemo(() => {
    return md.render(content)
  }, [content])

  return (
    <div
      className="markdown-content select-text"
      dangerouslySetInnerHTML={{ __html: htmlContent }}
      style={{
        fontSize: 14,
        lineHeight: 1.6,
        wordBreak: 'break-word'
      }}
    />
  )
}

const AIAssistant: FC<AIAssistantProps> = (props) => {
  const { visible, onClose, pageName } = props
  const [message, setMessage] = useState('')
  const {
    messages,
    streamingMessage,
    isLoading,
    error,
    sendMessage,
    stopStreaming,
    clearChat,
    setChatState,
    messageId: currentMessageId
  } = useChatStream()
  const [conversationId, setConversationId] = useState<number>()
  const { runAsync: createConversation } = useRequest(conversationService.createConversation, { manual: true })
  const { runAsync: interruptMessageGeneration } = useRequest(messageService.interruptMessageGeneration, {
    manual: true
  })
  const { runAsync: getConversationMessages } = useRequest(messageService.getConversationMessages, {
    manual: true,
    onSuccess: (msgs) => {
      setChatState((prev) => ({
        ...prev,
        messages: msgs as any[]
      }))
    }
  })

  // Get current page context information
  const getCurrentContext = useMemoizedFn((): ChatContext => {
    const context: ChatContext = {}

    // Get current URL and page information
    const currentPath = window.location.hash
    if (currentPath.includes('/vault')) {
      // If on the edit page, try to get document information
      const urlParams = new URLSearchParams(currentPath.split('?')[1] || '')
      const docId = urlParams.get('id')
      if (docId) {
        context.document_id = docId
        context.current_document = {
          id: docId
        }
      }
    }

    // Get selected text content
    const selection = window.getSelection()
    if (selection && selection.toString().trim()) {
      context.selected_content = selection.toString().trim()
    }

    return context
  })

  const handleSendMessage = useMemoizedFn(async () => {
    if (!message.trim() || isLoading) return
    if (!conversationId) {
      // Create a new conversation if none exists
      try {
        const response = await createConversation({ page_name: pageName })
        setConversationId(response.id)
        const context = getCurrentContext()
        if (response.id) {
          await sendMessage(message, response.id, context)
        }
        setMessage('')
      } catch (error) {
        logger.error('Failed to create conversation:', error)
        return
      }
    } else {
      const context = getCurrentContext()
      await sendMessage(message, conversationId, context)
      setMessage('')
    }
  })

  const handleKeyPress = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSendMessage()
      }
    },
    [handleSendMessage]
  )

  // Get workflow stage display text
  const getStageText = useCallback((stage?: string) => {
    switch (stage) {
      case 'intent_analysis':
        return 'Analyzing intent'
      case 'context_gathering':
        return 'Collecting context'
      case 'execution':
        return 'Executing'
      case 'reflection':
        return 'Reflecting'
      case 'completed':
        return 'Completed'
      case 'failed':
        return 'Failed'
      default:
        return 'Processing'
    }
  }, [])

  // Get workflow stage color
  const getStageColor = useCallback((stage?: string) => {
    switch (stage) {
      case 'intent_analysis':
        return 'blue'
      case 'context_gathering':
        return 'orange'
      case 'execution':
        return 'green'
      case 'reflection':
        return 'purple'
      case 'completed':
        return 'green'
      case 'failed':
        return 'red'
      default:
        return 'gray'
    }
  }, [])

  // Start a new conversation (clear the current one)
  const startNewConversation = useCallback(() => {
    clearChat()
    setConversationId(undefined)
    setMessage('')
  }, [clearChat])

  // Merge all messages (history + streaming)
  const allMessages = useMemo(() => {
    const result = [...messages]
    if (streamingMessage && streamingMessage.content.trim()) {
      result.push({
        role: streamingMessage.role,
        content: streamingMessage.content
      })
    }
    return result
  }, [messages, streamingMessage])

  const interruptMessage = useMemoizedFn(async () => {
    if (currentMessageId !== -1) {
      try {
        await interruptMessageGeneration(currentMessageId)
        stopStreaming()
      } catch (error) {
        logger.error('Failed to interrupt message generation:', error)
      }
    }
  })

  return (
    <div
      className={`relative h-[calc(100%-16px)] bg-white flex flex-col flex-shrink-0 transition-all duration-300 rounded-2xl ml-2 my-2 overflow-hidden select-text ${visible ? 'min-w-[332px]' : 'w-0 relative select-text'}`}>
      {/* Header */}
      <AIAssistantHeader
        onClose={onClose}
        startNewConversation={startNewConversation}
        conversationId={conversationId || -1}
        handleGetMessages={getConversationMessages}
        pageName={pageName}
      />

      <div className="flex-1 overflow-y-auto p-5 w-full">
        {allMessages.length === 0 ? (
          <div className="flex flex-col items-center text-center h-full justify-center">
            <div className="mb-6">
              <img src={chatEditIcon} alt="chat-edit" className="w-12 h-12" />
            </div>
            <Text style={{ fontSize: 14, fontWeight: 500, marginBottom: 8 }}>I am your Context - Aware AI partner</Text>
            <Text type="secondary" style={{ textAlign: 'center', lineHeight: 1.5 }}>
              Try asking me
            </Text>
            <div className="mt-6">
              <div
                className="py-1 px-3  mb-2 cursor-pointer transition-all duration-200 text-[13px] text-gray-800 rounded-lg border border-gray-200 bg-white bg-opacity-50 hover:rounded-lg hover:border-gray-200 hover:bg-white hover:bg-opacity-50"
                onClick={() => setMessage('Summarize my recent growth')}>
                Summarize my recent growth
              </div>
              <div
                className="py-1 px-3  mb-2 cursor-pointer transition-all duration-200 text-[13px] text-gray-800 rounded-lg border border-gray-200 bg-white bg-opacity-50 hover:rounded-lg hover:border-gray-200 hover:bg-white hover:bg-opacity-50"
                onClick={() => setMessage('List what I have done in the last two hours')}>
                List what I have done in the last two hours
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col w-full gap-4 select-text">
            {allMessages.map((msg, index) => (
              <div
                key={index}
                className={`flex bg-white w-full select-text ${msg.role === 'user' ? 'justify-end' : 'justify-start w-full'}`}>
                <div
                  className={`px-4 py-3 rounded-xl leading-6 relative select-text ${
                    msg.role === 'user'
                      ? 'bg-blue-50 text-white rounded-br-sm'
                      : 'bg-transparent w-full text-gray-800 rounded-bl-sm'
                  }`}>
                  {msg.role === 'assistant' ? (
                    <MarkdownContent content={msg.content} />
                  ) : (
                    <Text style={{ whiteSpace: 'pre-wrap' }} className="select-text">
                      {msg.content}
                    </Text>
                  )}
                  {/* Display stage information for streaming messages */}
                  {streamingMessage && index === allMessages.length - 1 && streamingMessage.stage && (
                    <div style={{ marginTop: 8 }}>
                      <Tag color={getStageColor(streamingMessage.stage)} size="small">
                        {getStageText(streamingMessage.stage)}
                      </Tag>
                    </div>
                  )}
                  {/* Copy button */}
                </div>
                {/* <div className="message-actions">
                  <Button type="text" size="mini" icon={<IconCopy />} onClick={() => copyToClipboard(msg.content)} />
                </div> */}
              </div>
            ))}

            {/* Error message display */}
            {error && (
              <div className="flex bg-white justify-start w-full">
                <div className="px-4 py-3 rounded-xl leading-6 relative select-text bg-red-50 border-red-200">
                  <Text style={{ color: '#ff4d4f', marginBottom: 8, display: 'block' }}>❌ {error}</Text>
                  <Button
                    size="small"
                    type="primary"
                    onClick={() => {
                      // Retry the last message
                      const lastUserMessage = messages.findLast((msg) => msg.role === 'user')
                      if (lastUserMessage) {
                        const context = getCurrentContext()
                        sendMessage(lastUserMessage.content, conversationId!, context)
                      }
                    }}
                    style={{ fontSize: 12 }}>
                    Retry
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="p-4 bg-white border-t border-gray-100 select-none">
        <div className="flex flex-col gap-2 bg-gray-50 rounded-xl p-3 border border-gray-200 transition-all duration-200">
          <div className="flex-1">
            <TextArea
              placeholder={isLoading ? 'AI is thinking...' : 'Ask me anything'}
              value={message}
              onChange={setMessage}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
              className="!bg-transparent !border-none !p-0 text-sm leading-6 resize-none focus:!shadow-none [&_.arco-textarea-wrapper]:bg-transparent"
              autoFocus
            />
          </div>
          <div className="flex justify-end items-center gap-2">
            {isLoading ? (
              <Button
                type="primary"
                size="small"
                icon={<IconStop />}
                onClick={interruptMessage}
                className="rounded-lg font-medium !bg-red-500 !border-red-500 hover:!bg-red-400 hover:!border-red-400"
              />
            ) : (
              <Button
                type="primary"
                size="small"
                icon={<img src={chatSendIcon} alt="chat-send" className="w-4 h-4" />}
                onClick={handleSendMessage}
                disabled={!message.trim()}
                className="rounded-lg font-medium"
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default AIAssistant
