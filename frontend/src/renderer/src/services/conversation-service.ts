import axios, { AxiosInstance } from 'axios'
import axiosInstance from './axiosConfig'

// 类型定义
export interface CreateConversationRequest {
  page_name: string
}

export interface ConversationResponse {
  id: number
  title?: string
  user_id?: string
  created_at: string
  updated_at: string
  metadata: string
  page_name: string
  status: string
}

export type ConversationSummary = ConversationResponse

export interface GetConversationListResponse {
  items: ConversationSummary[]
  total: number
}

export interface UpdateConversationRequest {
  title: string
}

export interface DeleteConversationResponse {
  success: boolean
  id: number
}

/**
 * 对话管理服务类，封装了与对话相关的所有 API 操作
 */
export class ConversationService {
  private axiosInstance: AxiosInstance
  private baseUrl: string = '/api/agent/chat'

  constructor(baseUrl?: string) {
    // 创建 axios 实例，可传入自定义配置（如拦截器、超时等）
    this.axiosInstance = axiosInstance

    if (baseUrl) {
      this.baseUrl = baseUrl
    }
  }

  /**
   * 创建新对话
   * @param request 创建对话请求参数
   * @returns 新创建的对话信息
   */
  createConversation = async (request: CreateConversationRequest): Promise<ConversationResponse> => {
    try {
      const response = await this.axiosInstance.post<ConversationResponse>(`${this.baseUrl}/conversations`, request)
      return response.data
    } catch (error) {
      this.handleError(error, '创建对话失败')
      throw error
    }
  }

  /**
   * 获取对话列表
   * @param params 分页和过滤参数
   * @returns 对话列表及总数
   */
  getConversationList = async (params: {
    limit?: number
    offset?: number
    page_name?: string
    user_id?: string
    status?: 'active' | 'deleted'
  }): Promise<GetConversationListResponse> => {
    try {
      const response = await this.axiosInstance.get<GetConversationListResponse>(`${this.baseUrl}/conversations/list`, {
        params: {
          limit: 20, // 默认值
          offset: 0, // 默认值
          status: 'active', // 默认值
          ...params
        }
      })
      return response.data
    } catch (error) {
      this.handleError(error, '获取对话列表失败')
      throw error
    }
  }

  /**
   * 获取对话详情
   * @param cid 对话 ID
   * @returns 对话详细信息
   */
  getConversationDetail = async (cid: number): Promise<ConversationResponse> => {
    try {
      const response = await this.axiosInstance.get<ConversationResponse>(`${this.baseUrl}/conversations/${cid}`)
      return response.data
    } catch (error) {
      this.handleError(error, `获取对话 ${cid} 详情失败`)
      throw error
    }
  }

  /**
   * 更新对话标题
   * @param cid 对话 ID
   * @param request 更新标题请求参数
   * @returns 更新后的对话信息
   */
  updateConversationTitle = async (cid: number, request: UpdateConversationRequest): Promise<ConversationResponse> => {
    try {
      const response = await this.axiosInstance.patch<ConversationResponse>(
        `${this.baseUrl}/conversations/${cid}/update`,
        request
      )
      return response.data
    } catch (error) {
      this.handleError(error, `更新对话 ${cid} 标题失败`)
      throw error
    }
  }

  /**
   * 删除对话（软删除）
   * @param cid 对话 ID
   * @returns 删除操作结果
   */
  deleteConversation = async (cid: number): Promise<DeleteConversationResponse> => {
    try {
      const response = await this.axiosInstance.delete<DeleteConversationResponse>(
        `${this.baseUrl}/conversations/${cid}/update`
      )
      return response.data
    } catch (error) {
      this.handleError(error, `删除对话 ${cid} 失败`)
      throw error
    }
  }

  /**
   * 错误处理工具方法
   * @param error 错误对象
   * @param message 错误提示信息
   */
  private handleError(error: any, message: string): void {
    // 可以根据需要扩展错误处理逻辑，如日志记录、错误转换等
    if (axios.isAxiosError(error)) {
      console.error(`${message}:`, error.response?.data || error.message)
    } else {
      console.error(`${message}:`, error)
    }
  }
}

// 默认导出实例（可根据需要配置全局拦截器）
export const conversationService = new ConversationService()
