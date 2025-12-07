// import { PATH } from '../../constants';
// import { getRequest } from '../core/apiClient';
// import { HealthCheckResponse, StatisticsResponse, ConfigSyncResponse } from '../types';

// 获取请求实例
// const request = getRequest();

/**
 * 系统相关API服务
 */
export const systemService = {
  // /**
  //  * 健康检查
  //  */
  // healthCheck: async (): Promise<HealthCheckResponse> => {
  //   return request.get<HealthCheckResponse>(PATH.HEALTH_CHECK);
  // },

  // /**
  //  * 获取统计信息
  //  */
  // getStatistics: async (): Promise<StatisticsResponse> => {
  //   return request.get<StatisticsResponse>(PATH.STATISTICS);
  // },

  // /**
  //  * 同步配置
  //  */
  // syncConfig: async (): Promise<ConfigSyncResponse> => {
  //   return request.get<ConfigSyncResponse>(PATH.SYNC_CONFIG);
  // },

  // /**
  //  * 测试连接
  //  */
  // testConnection: async (): Promise<{ success: boolean; latency?: number }> => {
  //   const startTime = Date.now();
  //   try {
  //     await request.get(PATH.TEST_CONNECTION);
  //     const latency = Date.now() - startTime;
  //     return { success: true, latency };
  //   } catch (error) {
  //     return { success: false };
  //   }
  // },
};

export default systemService;
