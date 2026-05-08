import { PATH } from '../../constants';
import { getRequest } from '../core/apiClient';
import { ApiResponse } from '../types';

// 获取请求实例
const request = getRequest();

/**
 * 截图相关API服务
 */
export const screenshotService = {
  /**
   * 上传截图
   */
  uploadScreenshot: async (screenshotData: { data: string; metadata?: any }): Promise<ApiResponse> => {
    return request.post<ApiResponse>(PATH.SCREENSHOT_UPLOAD, screenshotData);
  },

  // /**
  //  * 获取截图列表
  //  */
  // getScreenshots: async (page: number = 1, limit: number = 20): Promise<ApiResponse> => {
  //   return request.get<ApiResponse>(PATH.SCREENSHOT_LIST, { params: { page, limit } });
  // },

  // /**
  //  * 删除截图
  //  */
  // deleteScreenshot: async (screenshotId: string): Promise<ApiResponse> => {
  //   return request.delete<ApiResponse>(`${PATH.SCREENSHOT_DELETE}/${screenshotId}`);
  // },

  // /**
  //  * 分析截图内容
  //  */
  // analyzeScreenshot: async (screenshotId: string, prompt?: string): Promise<ApiResponse> => {
  //   return request.post<ApiResponse>(`${PATH.SCREENSHOT_ANALYZE}/${screenshotId}`, { prompt });
  // },
};

export default screenshotService;
