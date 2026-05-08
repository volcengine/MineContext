// API服务类型定义

/**
 * HTTP方法类型
 */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

/**
 * 请求配置
 */
export interface RequestConfig {
  baseURL: string;
  timeout?: number;
  headers?: Record<string, string>;
}

/**
 * 请求选项
 */
export interface RequestOptions {
  method?: HttpMethod;
  headers?: Record<string, string>;
  data?: any;
  timeout?: number;
}

/**
 * API响应格式
 */
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  timestamp: number;
}

/**
 * 健康检查响应
 */
export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy';
  version: string;
  uptime: number;
  services: {
    storage: boolean;
    llm: boolean;
    embedding: boolean;
  };
}

/**
 * 上下文相关类型
 */
export interface ContextUploadRequest {
  context: {
    id?: string;
    title: string;
    content: string;
    url?: string;
    type: 'article' | 'code' | 'multimedia' | 'data';
    metadata?: Record<string, any>;
    timestamp: number;
  };
}

export interface ContextUploadResponse {
  id: string;
  processed: boolean;
  embeddingsGenerated: boolean;
  processingTime: number;
  chunks?: number;
}

export interface ContextListResponse {
  contexts: Array<{
    id: string;
    title: string;
    content: string;
    url?: string;
    type: string;
    timestamp: number;
    size: number;
  }>;
  total: number;
  page: number;
  pages: number;
}

/**
 * 搜索相关类型
 */
export interface SearchRequest {
  query: string;
  limit?: number;
  filters?: {
    type?: string;
    dateRange?: {
      start: number;
      end: number;
    };
  };
}

export interface SearchResult {
  context: {
    id: string;
    title: string;
    content: string;
    url?: string;
    type: string;
    timestamp: number;
  };
  score: number;
  highlights: string[];
}

/**
 * 统计信息类型
 */
export interface StatisticsResponse {
  totalContexts: number;
  totalSize: number;
  storageUsed: number;
  storageLimit: number;
  lastSyncTime?: number;
}

/**
 * 配置同步类型
 */
export interface ConfigSyncResponse {
  settings: Record<string, any>;
  prompts: Record<string, any>;
  version: string;
}

/**
 * 错误类型
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public code?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * 网络错误类型
 */
export class NetworkError extends Error {
  constructor(message: string, public originalError?: any) {
    super(message);
    this.name = 'NetworkError';
  }
}

/**
 * 超时错误类型
 */
export class TimeoutError extends Error {
  constructor(message: string = 'Request timeout') {
    super(message);
    this.name = 'TimeoutError';
  }
}