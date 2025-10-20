// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useCallback, useMemo } from 'react'
import { Button, Input, Typography, Tag } from '@arco-design/web-react'
import { IconClose, IconStop, IconPlus } from '@arco-design/web-react/icon'
import { useChatStream } from '@renderer/hooks/use-chat-stream'
import { ChatContext } from '@renderer/services/ChatStreamService'
import MarkdownIt from 'markdown-it'

const { Text } = Typography
const { TextArea } = Input

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

const AIAssistant: React.FC<AIAssistantProps> = ({ visible, onClose }) => {
  const [message, setMessage] = useState('')
  const { messages, streamingMessage, isLoading, error, sendMessage, stopStreaming, clearChat } = useChatStream()

  // Get current page context information
  const getCurrentContext = useCallback((): ChatContext => {
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
          id: docId,
          title: 'Currently edited document', // Should actually be obtained from the editor
          content: 'Document content...' // Should actually be obtained from the editor
        }
      }
    }

    // Get selected text content
    const selection = window.getSelection()
    if (selection && selection.toString().trim()) {
      context.selected_content = selection.toString().trim()
    }

    return context
  }, [])

  const handleSendMessage = useCallback(async () => {
    if (!message.trim() || isLoading) return

    const context = getCurrentContext()
    await sendMessage(message, context)
    setMessage('')
  }, [message, isLoading, sendMessage, getCurrentContext])

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

  return (
    <div
      className={`relative h-[calc(100%-16px)] bg-white flex flex-col flex-shrink-0 transition-all duration-300 rounded-2xl m-2 ml-2 overflow-hidden select-text ${visible ? 'min-w-[340px] w-full' : 'w-0 relative select-text'}`}>
      {/* Header */}
      <div className="flex items-center px-4 py-3 border-b border-gray-100 bg-white gap-2 select-none">
        <Button type="text" icon={<IconPlus />} onClick={startNewConversation} />
        <Button
          type="text"
          icon={<IconClose />}
          onClick={onClose}
          style={{
            color: '#86909c',
            marginLeft: 'auto'
          }}
        />
      </div>

      <div className="flex-1 overflow-y-auto p-5 w-full">
        {allMessages.length === 0 ? (
          <div className="flex flex-col items-center text-center h-full justify-center">
            <div className="mb-6">
              <svg xmlns="http://www.w3.org/2000/svg" width="70" height="70" viewBox="0 0 70 70" fill="none">
                <g clip-path="url(#clip0_3_134963)">
                  <path
                    d="M36.3212 57.3503C31.2404 60.1166 24.6254 60.3363 16.4762 58.0094C11.9549 51.1022 9.94359 46.5303 11.6722 38.7759C13.4008 31.0215 18.9998 27.5009 21.4998 16.5009"
                    stroke="#3F3F51"
                    stroke-width="3"
                    stroke-linecap="round"
                  />
                  <path
                    d="M56.0804 27.0694L34.7835 11.021C31.1079 8.25121 25.8828 8.98554 23.113 12.6612C20.3433 16.3368 21.0776 21.5618 24.7532 24.3316L46.0502 40.38C49.7258 43.1498 54.9508 42.4154 57.7206 38.7398C60.4904 35.0642 59.756 29.8392 56.0804 27.0694Z"
                    stroke="#3F3F51"
                    stroke-width="3"
                  />
                  <path
                    fill-rule="evenodd"
                    clip-rule="evenodd"
                    d="M50.4666 12.809C51.2017 13.363 51.6041 14.2137 51.6603 15.1414C51.7166 16.069 51.4268 17.0736 50.7775 17.9352L48.4263 21.0553L41.771 16.0402L44.1222 12.9201C44.7715 12.0585 45.6572 11.503 46.5645 11.3014C47.4717 11.0997 48.4004 11.252 49.1355 11.806L50.4666 12.809Z"
                    stroke="#3F3F51"
                    stroke-width="3"
                  />
                  <path
                    d="M44.0621 46.5345C44.3843 45.6639 45.6157 45.6639 45.9379 46.5345L47.0012 49.408C47.1024 49.6818 47.3182 49.8976 47.592 49.9988L50.4655 51.0621C51.3361 51.3843 51.3361 52.6157 50.4655 52.9379L47.592 54.0012C47.3182 54.1024 47.1024 54.3182 47.0012 54.592L45.9379 57.4655C45.6157 58.3361 44.3843 58.3361 44.0621 57.4655L42.9988 54.592C42.8976 54.3182 42.6818 54.1024 42.408 54.0012L39.5345 52.9379C38.6639 52.6157 38.6639 51.3843 39.5345 51.0621L42.408 49.9988C42.6818 49.8976 42.8976 49.6818 42.9988 49.408L44.0621 46.5345Z"
                    fill="#3F3F51"
                  />
                </g>
                <defs>
                  <clipPath id="clip0_3_134963">
                    <rect width="70" height="70" fill="white" />
                  </clipPath>
                </defs>
              </svg>
            </div>
            <Text style={{ fontSize: 14, fontWeight: 500, marginBottom: 8 }}>I am your Context - Aware AI partner</Text>
            <Text type="secondary" style={{ textAlign: 'center', lineHeight: 1.5 }}>
              Try asking me
            </Text>
            <div className="mt-6">
              <div
                className="py-1 px-3 bg-gray-50 mb-2 cursor-pointer transition-all duration-200 text-[13px] text-gray-800 rounded-lg border border-gray-200 bg-white bg-opacity-50 hover:rounded-lg hover:border-gray-200 hover:bg-white hover:bg-opacity-50"
                onClick={() => setMessage('Summarize my recent growth')}>
                Summarize my recent growth
              </div>
              <div
                className="py-1 px-3 bg-gray-50 mb-2 cursor-pointer transition-all duration-200 text-[13px] text-gray-800 rounded-lg border border-gray-200 bg-white bg-opacity-50 hover:rounded-lg hover:border-gray-200 hover:bg-white hover:bg-opacity-50"
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
              <div className="flex bg-white w-full justify-start w-full">
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
                        sendMessage(lastUserMessage.content, context)
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
                onClick={stopStreaming}
                className="rounded-lg font-medium !bg-red-500 !border-red-500 hover:!bg-red-400 hover:!border-red-400"
              />
            ) : (
              <Button
                type="primary"
                size="small"
                icon={
                  <svg xmlns="http://www.w3.org/2000/svg" width="10" height="14" viewBox="0 0 10 14" fill="none">
                    <path
                      d="M0.0756551 5.35354L1.06015 6.33804L4.3108 3.08738L4.31088 13.8807L5.68927 13.88L5.68958 3.08848L8.93986 6.33876L9.92547 5.35315L5.00076 0.428444L0.0756551 5.35354Z"
                      fill="white"
                    />
                  </svg>
                }
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
