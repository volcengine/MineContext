import { PATH } from '../../constants';
import { getRequest } from '../core/apiClient';
import { ContextUploadRequest, ContextUploadResponse } from '../types';

// 获取请求实例
const request = getRequest();

/**
 * 上下文相关API服务
 */
export const contextService = {
  /**
   * 上传上下文
   */
  uploadContext: async (context: ContextUploadRequest['context']): Promise<ContextUploadResponse> => {
    return request.post<ContextUploadResponse>(PATH.UPLOAD_CONTEXT, { context });
  },

  /**
   * 获取上下文列表
   */
  // getContexts: async (page: number = 1, limit: number = 20): Promise<ContextListResponse> => {
  //   return request.get<ContextListResponse>(PATH.CONTEXT_LIST, { params: { page, limit } });
  // },

  /**
   * 搜索上下文
   */
  // searchContexts: async (searchRequest: SearchRequest): Promise<SearchResult[]> => {
  //   return request.post<SearchResult[]>(PATH.SEARCH_CONTEXT, searchRequest);
  // },

  /**
   * 删除上下文
   */
  // deleteContext: async (contextId: string): Promise<{ success: boolean }> => {
  //   return request.delete<{ success: boolean }>(`${PATH.CONTEXT_DELETE}/${contextId}`);
  // },

  /**
   * 获取上下文详情
   */
  // getContextDetail: async (contextId: string): Promise<any> => {
  //   return request.get(`${PATH.CONTEXT_DETAIL}/${contextId}`);
  // },
};

export default contextService;
