// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import axios from 'axios'

// TODO：最后使用主进程代理，这样不需要每次都更新baseURL
// 创建axios实例，初始使用默认端口
const axiosInstance = axios.create({
  baseURL: 'http://127.0.0.1:8000', // 默认端口，将在运行时更新
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
  // 解决CORS问题的配置
  withCredentials: false,
})

// 动态更新baseURL的函数
export const updateBaseURL = (port: number) => {
  const newBaseURL = `http://127.0.0.1:${port}`;
  axiosInstance.defaults.baseURL = newBaseURL;
  console.log(`Updated axios baseURL to: ${newBaseURL}`);
}

// 在应用启动时获取后端端口并更新baseURL
if (typeof window !== 'undefined' && window.electron) {
  window.electron.ipcRenderer.invoke('backend:get-port').then((port: number) => {
    if (port && port !== 8000) {
      updateBaseURL(port);
    }
  }).catch((error) => {
    console.warn('Failed to get backend port, using default 8000:', error);
  });
}

// 请求拦截器
axiosInstance.interceptors.request.use(
  (config) => {
    // 发送请求之前
    return config
  },
  (error) => {
    // 请求错误
    return Promise.reject(error)
  }
)

// 响应拦截器
axiosInstance.interceptors.response.use(
  (response) => {
    // 响应数据
    return response
  },
  (error) => {
    // 响应错误
    return Promise.reject(error)
  }
)

export default axiosInstance
