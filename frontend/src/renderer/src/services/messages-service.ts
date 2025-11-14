import axios, { AxiosInstance } from 'axios'
import axiosInstance from './axiosConfig'

// Type definitions matching the Python Pydantic models
export interface CreateMessageParams {
  conversation_id: number
  role: string
  content: string
  is_complete?: boolean
  token_count?: number
}

export interface CreateStreamingMessageParams {
  conversation_id: number
  role: string
}

export interface UpdateMessageContentParams {
  message_id: number
  new_content: string
  is_complete?: boolean
  token_count?: number
}

export interface AppendMessageContentParams {
  message_id: number
  content_chunk: string
  token_count?: number
}

export interface ConversationMessage {
  id: number
  conversation_id: number
  parent_message_id?: string
  role: string
  content: string
  status: string
  token_count: number
  metadata: string
  latency_ms: number
  error_message: string
  thinking: Array<Record<string, any>>
  completed_at?: string
  created_at?: string
  updated_at?: string
}

export interface MessageInterruptResponse {
  message_id: string
}

/**
 * Service for managing conversation messages, handling CRUD operations and streaming
 */
export class MessageService {
  private axiosInstance: AxiosInstance
  private baseUrl: string = '/api/agent/chat'

  /**
   * Initialize the MessageService
   * @param config - Optional Axios request configuration
   * @param baseUrl - Optional base URL override for the API endpoints
   */
  constructor(baseUrl?: string) {
    this.axiosInstance = axiosInstance

    if (baseUrl) this.baseUrl = baseUrl
  }

  /**
   * Create a new message in a conversation
   * @param mid - Parent message ID from URL
   * @param params - Message creation parameters
   * @returns ID of the created message
   */
  createMessage = async (mid: string, params: CreateMessageParams): Promise<number> => {
    try {
      const response = await this.axiosInstance.post<number>(`${this.baseUrl}/message/${mid}/create`, params)
      return response.data
    } catch (error) {
      this.handleError(error, 'Failed to create message')
      throw error
    }
  }

  /**
   * Create a new streaming message placeholder
   * @param mid - Parent message ID from URL
   * @param params - Streaming message parameters
   * @returns ID of the created streaming message
   */
  createStreamingMessage = async (mid: string, params: CreateStreamingMessageParams): Promise<number> => {
    try {
      const response = await this.axiosInstance.post<number>(`${this.baseUrl}/message/stream/${mid}/create`, params)
      return response.data
    } catch (error) {
      this.handleError(error, 'Failed to create streaming message')
      throw error
    }
  }

  /**
   * Update an existing message's content
   * @param mid - Message ID from URL
   * @param params - Update parameters
   * @returns Success status of the update
   */
  updateMessage = async (mid: number, params: UpdateMessageContentParams): Promise<boolean> => {
    try {
      const response = await this.axiosInstance.post<boolean>(`${this.baseUrl}/message/${mid}/update`, params)
      return response.data
    } catch (error) {
      this.handleError(error, `Failed to update message ${mid}`)
      throw error
    }
  }

  /**
   * Append content to a streaming message
   * @param mid - Message ID from URL
   * @param params - Append parameters
   * @returns Success status of the append operation
   */
  appendMessage = async (mid: number, params: AppendMessageContentParams): Promise<boolean> => {
    try {
      const response = await this.axiosInstance.post<boolean>(`${this.baseUrl}/message/${mid}/append`, params)
      return response.data
    } catch (error) {
      this.handleError(error, `Failed to append to message ${mid}`)
      throw error
    }
  }

  /**
   * Mark a message as finished/completed
   * @param mid - Message ID from URL
   * @returns Success status of the operation
   */
  markMessageFinished = async (mid: number): Promise<boolean> => {
    try {
      const response = await this.axiosInstance.post<boolean>(`${this.baseUrl}/message/${mid}/finished`)
      return response.data
    } catch (error) {
      this.handleError(error, `Failed to mark message ${mid} as finished`)
      throw error
    }
  }

  /**
   * Get all messages for a specific conversation
   * @param cid - Conversation ID
   * @returns List of conversation messages
   */
  getConversationMessages = async (cid: number): Promise<ConversationMessage[]> => {
    try {
      const response = await this.axiosInstance.get<ConversationMessage[]>(
        `${this.baseUrl}/conversations/${cid}/messages`
      )
      return response.data
    } catch (error) {
      this.handleError(error, `Failed to get messages for conversation ${cid}`)
      throw error
    }
  }

  /**
   * Interrupt an ongoing message generation
   * @param mid - Message ID to interrupt
   * @returns Interrupt response with message ID
   */
  interruptMessageGeneration = async (mid: number): Promise<MessageInterruptResponse> => {
    try {
      const response = await this.axiosInstance.post<MessageInterruptResponse>(
        `${this.baseUrl}/messages/${mid}/interrupt`
      )
      return response.data
    } catch (error) {
      this.handleError(error, `Failed to interrupt message ${mid}`)
      throw error
    }
  }

  /**
   * Central error handling for API requests
   * @param error - Error object from Axios
   * @param message - Custom error message
   */
  private handleError = (error: any, message: string): void => {
    if (axios.isAxiosError(error)) {
      console.error(`${message}:`, error.response?.data || error.message)
    } else {
      console.error(`${message}:`, error)
    }
  }
}

// Default service instance with standard configuration
export const messageService = new MessageService()
