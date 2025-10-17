// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

'use client'

// import { streamText } from 'ai';
// import { createOpenAICompatible } from '@ai-sdk/openai-compatible';
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton
} from '@renderer/components/ai-elements/conversation'
import { Message, MessageContent } from '@renderer/components/ai-elements/message'
import {
  PromptInput,
  PromptInputButton,
  PromptInputModelSelect,
  PromptInputModelSelectContent,
  PromptInputModelSelectItem,
  PromptInputModelSelectTrigger,
  PromptInputModelSelectValue,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputToolbar,
  PromptInputTools
} from '@renderer/components/ai-elements/prompt-input'
import { Actions, Action } from '@renderer/components/ai-elements/actions'
import { Fragment, useState } from 'react'
import { Response } from '@renderer/components/ai-elements/response'
import { GlobeIcon, RefreshCcwIcon, CopyIcon } from 'lucide-react'
import ChatBubbleIcon from '@renderer/assets/icons/chat-bubble.svg'
import { Source, Sources, SourcesTrigger, SourcesContent } from '@renderer/components/ai-elements/sources'
import { Reasoning, ReasoningContent, ReasoningTrigger } from '@renderer/components/ai-elements/reasoning'
import { Loader } from '@renderer/components/ai-elements/loader'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'

const models = [
  {
    name: '豆包 Pro',
    value: 'ep-20250905001701-zgzfx'
  }
]

// async function APIChatHandler(model: string) {
//   try {
//     // const openai = createOpenAI({
//     //   baseURL: "https://ark.cn-beijing.volces.com/api/v3",
//     // });
//     // const openai = createOpenAI({
//     // });

//     const openai = createOpenAICompatible({
//       baseURL: "https://ark.cn-beijing.volces.com/api/v3",
//       name: 'ark',
//     });

//     // const newMessages = convertToModelMessages(messages);

//     // console.log(JSON.stringify(newMessages));
//     const result = streamText({
//       // model: openai.chat(model),
//       model: openai.chatModel(model),
//       messages: [{"role":"user","content":[{"type":"text","text":"hi"}]}],
//       system:
//         'You are a helpful assistant that can answer questions and help with tasks',
//       providerOptions: {
//         openai: {
//           reasoning: true,
//           reasoningEffort: 'high',
//         },
//       },
//     });

//     console.log(JSON.stringify(result), 'result');

//     // send sources and reasoning back to the client
//     const response = await result.toUIMessageStreamResponse({
//       sendSources: true,
//       sendReasoning: true,
//     });

//     // 如果response是ReadableStream，需要处理流
//     if (response.body) {
//       const reader = response.body.getReader()
//       const decoder = new TextDecoder()

//       try {
//         while (true) {
//           const { done, value } = await reader.read()
//           if (done) break

//           const chunk = decoder.decode(value, { stream: true })
//           console.log(chunk, 'chunk');
//         }
//       } finally {
//         reader.releaseLock()
//       }
//     }
//   } catch (error) {
//     console.error('Error in APIChatHandler:', error)
//   }
// }

const ChatBotDemo = () => {
  const [input, setInput] = useState('')
  const [model, setModel] = useState<string>(models[0].value)
  const [webSearch, setWebSearch] = useState(false)
  const { messages, sendMessage, status } = useChat({
    transport: new DefaultChatTransport({
      api: 'http://127.0.0.1:3001/api/chat'
    })
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // APIChatHandler(model);
    // return;
    if (input.trim()) {
      sendMessage(
        { text: input },
        {
          body: {
            model: model,
            webSearch: webSearch
          }
        }
      )
      setInput('')
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6 relative size-full h-screen bg-white shadow-2xl border border-gray-200 rounded-2xl">
      <div className="flex flex-col h-full">
        <Conversation className="h-full">
          <ConversationContent className="bg-white">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="bg-gray-50 rounded-2xl p-8 shadow-lg border border-gray-200">
                  <div className="bg-black rounded-full p-4 w-fit mx-auto mb-6">
                    <img src={ChatBubbleIcon} alt="Chat" className="size-8 text-white" />
                  </div>
                  <h3 className="text-2xl font-bold mb-3 text-black">AI Chat Assistant</h3>
                  <p className="text-gray-600 leading-relaxed">Start a conversation with our intelligent AI</p>
                </div>
              </div>
            )}

            {messages.map((message) => (
              <div key={message.id}>
                {message.role === 'assistant' &&
                  message.parts.filter((part) => part.type === 'source-url').length > 0 && (
                    <Sources className="mb-4">
                      <SourcesTrigger
                        className="[&_.arco-btn]: !bg-gray-100 [&_.arco-btn]: !border-gray-300 [&_.arco-btn]: !text-gray-700 [&_.arco-btn:hover]: !bg-gray-200"
                        count={message.parts.filter((part) => part.type === 'source-url').length}
                      />
                      {message.parts
                        .filter((part) => part.type === 'source-url')
                        .map((part, i) => (
                          <SourcesContent key={`${message.id}-${i}`}>
                            <Source
                              key={`${message.id}-${i}`}
                              href={part.url}
                              title={part.url}
                              className="[&_.arco-btn]: !bg-white [&_.arco-btn]: !border-gray-200 [&_.arco-btn]: !text-gray-800 [&_.arco-btn:hover]: !bg-gray-50"
                            />
                          </SourcesContent>
                        ))}
                    </Sources>
                  )}
                {message.parts.map((part, i) => {
                  switch (part.type) {
                    case 'text':
                      return (
                        <Fragment key={`${message.id}-${i}`}>
                          <Message from={message.role}>
                            <MessageContent
                              className={`${
                                message.role === 'user'
                                  ? 'bg-black text-white shadow-lg border-0'
                                  : 'bg-gray-50 text-black shadow-md border border-gray-200'
                              } transition-all duration-200 hover:shadow-xl`}>
                              <Response>{part.text}</Response>
                            </MessageContent>
                          </Message>
                          {message.role === 'assistant' && i === message.parts.length - 1 && (
                            <Actions className="mt-3">
                              <Action
                                onClick={() => {}}
                                label="Retry"
                                className="[&_.arco-btn]: !bg-white [&_.arco-btn:hover]: !bg-gray-100 [&_.arco-btn]: !text-gray-600 [&_.arco-btn:hover]: !text-black [&_.arco-btn]: !border [&_.arco-btn]: !border-gray-300 [&_.arco-btn:hover]: !border-gray-400 transition-all duration-200">
                                <RefreshCcwIcon className="size-3" />
                              </Action>
                              <Action
                                onClick={() => navigator.clipboard.writeText(part.text || '')}
                                label="Copy"
                                className="[&_.arco-btn]: !bg-white [&_.arco-btn:hover]: !bg-gray-100 [&_.arco-btn]: !text-gray-600 [&_.arco-btn:hover]: !text-black [&_.arco-btn]: !border [&_.arco-btn]: !border-gray-300 [&_.arco-btn:hover]: !border-gray-400 transition-all duration-200">
                                <CopyIcon className="size-3" />
                              </Action>
                            </Actions>
                          )}
                        </Fragment>
                      )
                    case 'reasoning':
                      return (
                        <Reasoning
                          key={`${message.id}-${i}`}
                          className="w-full bg-gray-50 border border-gray-200 rounded-xl"
                          isStreaming={
                            status === 'streaming' &&
                            i === message.parts.length - 1 &&
                            message.id === messages.at(-1)?.id
                          }>
                          <ReasoningTrigger className="text-gray-700 hover:text-black" />
                          <ReasoningContent className="text-gray-800">{part.text}</ReasoningContent>
                        </Reasoning>
                      )
                    default:
                      return null
                  }
                })}
              </div>
            ))}
            {status === 'submitted' && (
              <div className="flex items-center justify-center py-6 bg-gray-50 rounded-2xl mx-4 shadow-lg border border-gray-200">
                <Loader className="mr-3 text-black" size={20} />
                <span className="text-gray-700 font-medium">AI is thinking...</span>
              </div>
            )}
          </ConversationContent>
          <ConversationScrollButton />
        </Conversation>

        <div className="border-t border-gray-300 bg-gray-50 p-4 shadow-lg">
          <PromptInput
            onSubmit={handleSubmit}
            className="bg-white shadow-md border border-gray-300 rounded-xl overflow-hidden">
            <PromptInputTextarea
              onChange={(e) => setInput(e.target.value)}
              value={input}
              placeholder="Type your message..."
              className="text-black placeholder-gray-500 bg-white border-0 focus:ring-0"
            />
            <PromptInputToolbar className="bg-gray-50 border-t border-gray-200">
              <PromptInputTools>
                <PromptInputButton
                  variant={webSearch ? 'default' : 'ghost'}
                  onClick={() => setWebSearch(!webSearch)}
                  className={`${
                    webSearch
                      ? 'bg-black text-white shadow-md'
                      : 'bg-white text-gray-600 hover:bg-gray-100 hover:text-black'
                  } border border-gray-300 hover:border-gray-400 transition-all duration-200`}>
                  <GlobeIcon size={16} />
                  <span>Search</span>
                </PromptInputButton>
                <PromptInputModelSelect
                  onValueChange={(value) => {
                    setModel(value)
                  }}
                  value={model}>
                  <PromptInputModelSelectTrigger className="[&_.arco-select-view]: !text-gray-600 [&_.arco-select-view:hover]: !text-black [&_.arco-select-view]: !border-0 [&_.arco-select-view]: !bg-transparent [&_.arco-select-view:hover]: !bg-gray-100 transition-all duration-200">
                    <PromptInputModelSelectValue />
                  </PromptInputModelSelectTrigger>
                  <PromptInputModelSelectContent className="bg-white border border-gray-300 shadow-xl">
                    {models.map((model) => (
                      <PromptInputModelSelectItem
                        key={model.value}
                        value={model.value}
                        className="[&_.arco-select-option]: !text-gray-800 [&_.arco-select-option:hover]: !bg-gray-100 [&_.arco-select-option:focus]: !bg-gray-100 [&_.arco-select-option:hover]: !text-black">
                        {model.name}
                      </PromptInputModelSelectItem>
                    ))}
                  </PromptInputModelSelectContent>
                </PromptInputModelSelect>
              </PromptInputTools>
              <PromptInputSubmit
                disabled={!input}
                status={
                  status === 'submitted'
                    ? 'submitted'
                    : status === 'streaming'
                      ? 'streaming'
                      : status === 'error'
                        ? 'error'
                        : undefined
                }
                className="[&_.arco-btn-primary]: !bg-black [&_.arco-btn-primary:hover]: !bg-gray-800 [&_.arco-btn-primary]: !text-white [&_.arco-btn-primary:disabled]: !bg-gray-400 [&_.arco-btn-primary:disabled]: !text-gray-200 shadow-md hover:shadow-lg transition-all duration-200 rounded-lg"
              />
            </PromptInputToolbar>
          </PromptInput>
        </div>
      </div>
    </div>
  )
}

export default ChatBotDemo
