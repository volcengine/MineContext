// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import axiosInstance from './axiosConfig';

// Type definitions for the Chat Stream API
export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface DocumentInfo {
  id?: string;
  title?: string;
  content?: string;
  summary?: string;
  tags?: string[];
}

export interface ContextItem {
  source: "document" | "web_search" | "agent_memory" | "context_db" | "chat_history" | "processed" | "entity" | "unknown";
  content: string;
  title?: string;
  relevance_score: number;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface ChatContext {
  chat_history?: ChatMessage[];
  selected_content?: string;
  document_id?: string;
  current_document?: DocumentInfo;
  collected_contexts?: ContextItem[];
  [key: string]: any; // Other custom fields
}

export interface ChatStreamRequest {
  query: string;
  context?: ChatContext;
  session_id?: string;
  user_id?: string;
}

export type EventType =
  | "session_start"
  | "thinking"
  | "running"
  | "done"
  | "fail"
  | "completed"
  | "stream_chunk"
  | "stream_complete";

export type WorkflowStage =
  | "init"
  | "intent_analysis"
  | "context_gathering"
  | "execution"
  | "reflection"
  | "completed"
  | "failed"
  | "next";

export type NodeType = "intent" | "context" | "execute" | "reflect";

export interface StreamEvent {
  type: EventType;
  content: string;
  stage?: WorkflowStage;
  node?: NodeType;
  progress: number;
  timestamp: string;
  session_id?: string;
  metadata?: {
    [key: string]: any;
  };
}

// Streaming chat service class
export class ChatStreamService {
  private abortController?: AbortController

  // Send a streaming chat request
  async sendStreamMessage(
    request: ChatStreamRequest,
    onEvent: (event: StreamEvent) => void,
    onError?: (error: Error) => void,
    onComplete?: () => void
  ): Promise<void> {
    // Cancel the previous request
    this.abortStream();

    this.abortController = new AbortController();

    try {
      // Use the baseURL of axiosInstance to ensure consistent ports
      const baseUrl = axiosInstance.defaults.baseURL || 'http://127.0.0.1:8000';
      const response = await fetch(`${baseUrl}/api/agent/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is not readable');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // Handle multi-line data
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep the potentially incomplete last line

        for (const line of lines) {
          if (line.trim() === '') continue;

          console.log('📨 Received SSE line:', line);

          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6); // Remove 'data: ' prefix
              console.log('🔍 Parsing JSON:', jsonStr);
              const eventData = JSON.parse(jsonStr);
              console.log('✅ Parsed successfully:', eventData);
              onEvent(eventData as StreamEvent);
            } catch (parseError) {
              console.warn('❌ Failed to parse SSE data:', line, parseError);
            }
          } else {
            console.log('⚠️ Non-data line:', line);
          }
        }
      }

      onComplete?.();
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Stream request was aborted');
        return;
      }

      console.error('Stream request failed:', error);
      onError?.(error as Error);
    }
  }

  // Cancel the current streaming request
  abortStream(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = undefined;
    }
  }

  // Generate a session ID
  generateSessionId(): string {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }
}

// Export a singleton instance
export const chatStreamService = new ChatStreamService();
