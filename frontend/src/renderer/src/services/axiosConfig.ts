// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import axios from 'axios'

// TODO: Finally, use the main process proxy so that the baseURL does not need to be updated every time
// Resolve default backend URL from env (fallback to 127.0.0.1:8000)
const DEFAULT_HOST = (import.meta.env?.VITE_WEB_HOST as string) || '127.0.0.1'
const DEFAULT_PORT = Number(import.meta.env?.VITE_WEB_PORT ?? 8000)
const DEFAULT_BASE_URL = `http://${DEFAULT_HOST}:${DEFAULT_PORT}`

// Create an axios instance, initially using the env/default port
const axiosInstance = axios.create({
  baseURL: DEFAULT_BASE_URL,
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json'
  },
  // Configuration to solve CORS issues
  withCredentials: false
})

// Function to dynamically update the baseURL
export const updateBaseURL = (port: number) => {
  const newBaseURL = `http://127.0.0.1:${port}`
  axiosInstance.defaults.baseURL = newBaseURL
  console.log(`Updated axios baseURL to: ${newBaseURL}`)
}

// Get the backend port and update the baseURL when the application starts
if (typeof window !== 'undefined' && window.electron) {
  window.electron.ipcRenderer
    .invoke('backend:get-port')
    .then((port: number) => {
      if (port && port !== DEFAULT_PORT) {
        updateBaseURL(port)
      }
    })
    .catch((error) => {
      console.warn(`Failed to get backend port, using default ${DEFAULT_PORT}:`, error)
    })
}

// Request interceptor
axiosInstance.interceptors.request.use(
  (config) => {
    // Before sending the request
    return config
  },
  (error) => {
    // Request error
    return Promise.reject(error)
  }
)

// Response interceptor
axiosInstance.interceptors.response.use(
  (response) => {
    // Response data
    return response
  },
  (error) => {
    // Response error
    return Promise.reject(error)
  }
)

export default axiosInstance
