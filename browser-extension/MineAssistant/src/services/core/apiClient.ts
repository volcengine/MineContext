import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { DEFAULT_SETTINGS } from '../../constants';
import { getStorageManager } from '../../storage';

/**
 * API客户端管理器 - 使用单例模式确保只有一个实例
 */
class ApiClientManager {
  private static instance: ApiClientManager;
  private apiClient: AxiosInstance;
  private settingsManager: any = null;
  private isBackendUrlUpdating: boolean = false;
  private lastBackendUrl: string = DEFAULT_SETTINGS.backendUrl;
  private isInitialized: boolean = false;
  private initializationPromise: Promise<void> | null = null;

  private constructor() {
    // 私有构造函数，防止外部直接实例化
    this.apiClient = axios.create({
      baseURL: this.lastBackendUrl,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      }
    });

    this.setupInterceptors();
  }

  /**
   * 获取单例实例
   */
  public static getInstance(): ApiClientManager {
    if (!ApiClientManager.instance) {
      ApiClientManager.instance = new ApiClientManager();
    }
    return ApiClientManager.instance;
  }

  /**
   * 设置拦截器
   */
  private setupInterceptors(): void {
    // 请求拦截器
    this.apiClient.interceptors.request.use(
      async (config) => {
        // 检查 backendUrl 是否正在更新
        if (this.isBackendUrlUpdating) {
          const error = new Error('Backend URL is currently updating, request blocked');
          console.warn('[API] Request blocked:', error.message);
          return Promise.reject(error);
        }

        // 检查是否需要更新 baseURL
        const currentBackendUrl = await this.getBackendUrl();
        if (currentBackendUrl !== this.lastBackendUrl) {
          const error = new Error('Backend URL has changed, please update and retry');
          console.warn('[API] Request blocked - URL changed:', {
            lastUrl: this.lastBackendUrl,
            currentUrl: currentBackendUrl
          });
          return Promise.reject(error);
        }

        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`, {
          params: config.params,
          data: config.data,
          baseURL: config.baseURL
        });
        return config;
      },
      (error) => {
        console.error('[API] Request error:', error);
        return Promise.reject(error);
      }
    );

    // 响应拦截器
    this.apiClient.interceptors.response.use(
      (response) => {
        console.log(`[API] Success: ${response.config.method?.toUpperCase()} ${response.config.url}`, {
          status: response.status,
          data: response.data
        });
        return response;
      },
      (error) => {
        console.error('[API] Response error:', {
          url: error.config?.url,
          status: error.response?.status,
          message: error.message,
          data: error.response?.data
        });
        return Promise.reject(error);
      }
    );
  }

  /**
   * 确保获取到设置管理器
   */
  private async getSettingsManager(): Promise<any> {
    if (!this.settingsManager) {
      const storageManager = await getStorageManager();
      this.settingsManager = storageManager.settingsManager;
    }
    return this.settingsManager;
  }

  /**
   * 获取当前 backendUrl
   */
  private async getBackendUrl(): Promise<string> {
    try {
      const manager = await this.getSettingsManager();
      const settings = await manager.getSettings();
      return settings.backendUrl;
    } catch (error) {
      console.error('Failed to get backendUrl from settings:', error);
      return DEFAULT_SETTINGS.backendUrl;
    }
  }

  /**
   * 更新 axios baseURL
   */
  private async updateAxiosBaseUrl(): Promise<void> {
    const newBackendUrl = await this.getBackendUrl();
    const apiBaseUrl = `${newBackendUrl}/api`;

    if (this.apiClient.defaults.baseURL !== apiBaseUrl) {
      this.apiClient.defaults.baseURL = apiBaseUrl;
      console.log(`[API] Updated baseURL to: ${apiBaseUrl}`);
    }

    this.lastBackendUrl = newBackendUrl;
    this.isBackendUrlUpdating = false;
  }

  /**
   * 初始化API客户端
   */
  public async initialize(): Promise<void> {
    // 防止重复初始化
    if (this.isInitialized) {
      return;
    }

    // 如果已经有初始化过程在进行，等待其完成
    if (this.initializationPromise) {
      return this.initializationPromise;
    }

    // 创建初始化promise
    this.initializationPromise = (async () => {
      try {
        console.log('[API] Initializing API client...');

        // 确保 storage 已初始化
        const storageManager = await getStorageManager();

        this.isBackendUrlUpdating = true;
        await this.updateAxiosBaseUrl();

        // 设置设置变化监听器
        await this.setupSettingsListener();

        this.isInitialized = true;
        console.log('[API] API client initialization completed');
      } catch (error) {
        console.error('[API] Failed to initialize API client:', error);
        throw error;
      } finally {
        this.initializationPromise = null;
      }
    })();

    return this.initializationPromise;
  }

  /**
   * 监听设置变化
   */
  private async setupSettingsListener(): Promise<void> {
    try {
      const manager = await this.getSettingsManager();
      manager.onSettingsChanged((newSettings: any) => {
        console.log('[API] Settings changed, updating backendUrl...', newSettings);
        this.updateBackendUrl();
      });
    } catch (error) {
      console.error('[API] Failed to setup settings listener:', error);
    }
  }

  /**
   * 更新后端URL
   */
  public async updateBackendUrl(): Promise<void> {
    this.isBackendUrlUpdating = true;
    await this.updateAxiosBaseUrl();
  }

  /**
   * 获取axios实例（谨慎使用）
   */
  public getAxiosInstance(): AxiosInstance {
    return this.apiClient;
  }

  /**
   * 检查是否已初始化
   */
  public getIsInitialized(): boolean {
    return this.isInitialized;
  }

  /**
   * 通用请求方法
   */
  public request = {
    get: <T = any>(url: string, config?: AxiosRequestConfig) =>
      this.apiClient.get<T>(url, config).then(res => res.data),

    post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) =>
      this.apiClient.post<T>(url, data, config).then(res => res.data),

    put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) =>
      this.apiClient.put<T>(url, data, config).then(res => res.data),

    delete: <T = any>(url: string, config?: AxiosRequestConfig) =>
      this.apiClient.delete<T>(url, config).then(res => res.data),
  };
}

// 导出单例实例的方法和请求接口
const apiClientManager = ApiClientManager.getInstance();

export const initializeApiClient = async () => {
  return apiClientManager.initialize();
};

export const updateBackendUrl = async () => {
  return apiClientManager.updateBackendUrl();
};

export const getRequest = (): typeof apiClientManager.request => {
  return apiClientManager.request;
};
