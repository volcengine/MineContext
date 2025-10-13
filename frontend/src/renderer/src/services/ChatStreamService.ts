// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import axiosInstance from './axiosConfig';

// Chat Stream API 相关类型定义
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
  [key: string]: any; // 其他自定义字段
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

// 流式聊天服务类
export class ChatStreamService {
  private abortController?: AbortController;

  // 发送流式聊天请求
  async sendStreamMessage(
    request: ChatStreamRequest,
    onEvent: (event: StreamEvent) => void,
    onError?: (error: Error) => void,
    onComplete?: () => void
  ): Promise<void> {
    // 取消之前的请求
    this.abortStream();

    this.abortController = new AbortController();

    try {
      // 使用 axiosInstance 的 baseURL，确保端口一致
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

        // 处理多行数据
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 保留可能不完整的最后一行

        for (const line of lines) {
          if (line.trim() === '') continue;

          console.log('📨 收到SSE行:', line);

          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6); // 移除 'data: ' 前缀
              console.log('🔍 解析JSON:', jsonStr);
              const eventData = JSON.parse(jsonStr);
              console.log('✅ 解析成功:', eventData);
              onEvent(eventData as StreamEvent);
            } catch (parseError) {
              console.warn('❌ 解析SSE数据失败:', line, parseError);
            }
          } else {
            console.log('⚠️  非data行:', line);
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

  // 取消当前流式请求
  abortStream(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = undefined;
    }
  }

  // 生成会话ID
  generateSessionId(): string {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }
}

// 导出单例实例
export const chatStreamService = new ChatStreamService();
