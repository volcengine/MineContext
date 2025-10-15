// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import express, { Request, Response } from 'express'
import { createServer } from 'http'
import { streamText, UIMessage, convertToModelMessages } from 'ai'
import { createOpenAICompatible } from '@ai-sdk/openai-compatible'

export function createExpressServer() {
  const expressApp = express()
  const port = 3001 // Choose a port

  // Add JSON parsing middleware
  expressApp.use(express.json())
  expressApp.use(express.urlencoded({ extended: true }))

  // Add CORS middleware
  expressApp.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*')
    res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization')

    if (req.method === 'OPTIONS') {
      res.sendStatus(200)
    } else {
      next()
    }
  })

  expressApp.post('/api/chat', APIChatHandler)

  const server = createServer(expressApp)
  server.listen(port, () => {
    console.log(`Express server running on port ${port}`)
  })
  return server
}

// Allow streaming responses up to 30 seconds
export const maxDuration = 30

export async function APIChatHandler(req: Request, res: Response) {
  try {
    const { messages, model, webSearch }: { messages: UIMessage[]; model: string; webSearch: boolean } = req.body
    console.log(webSearch, 'webSearch')
    // const openai = createOpenAI({
    //   baseURL: "https://ark.cn-beijing.volces.com/api/v3",
    // });
    const openai = createOpenAICompatible({
      baseURL: 'https://ark.cn-beijing.volces.com/api/v3',
      name: 'ark',
      apiKey: ''
    })
    // const openai = createOpenAI({
    // });

    const newMessages = convertToModelMessages(messages)

    console.log(JSON.stringify(newMessages))
    const result = streamText({
      // model: openai.chat(model),
      model: openai.chatModel(model),
      messages: newMessages,
      system: 'You are a helpful assistant that can answer questions and help with tasks',
      providerOptions: {
        openai: {
          reasoning: true,
          reasoningEffort: 'high'
        }
      }
    })

    console.log(JSON.stringify(result), 'result')

    // send sources and reasoning back to the client
    const response = await result.toUIMessageStreamResponse({
      sendSources: true,
      sendReasoning: true
    })

    // Forward the response to the client
    res.setHeader('Content-Type', 'text/plain; charset=utf-8')
    res.setHeader('Cache-Control', 'no-cache')
    res.setHeader('Connection', 'keep-alive')

    // If the response is a ReadableStream, handle the stream
    if (response.body) {
      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value, { stream: true })
          console.log(chunk, 'chunk')
          res.write(chunk)
        }
      } finally {
        reader.releaseLock()
        res.end()
      }
    } else {
      res.end()
    }
  } catch (error) {
    console.error('Error in APIChatHandler:', error)
    res.status(500).json({ error: 'Internal server error' })
  }
}
