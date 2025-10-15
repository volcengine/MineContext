// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import axios from 'axios'

// TODO: Finally, use the main process proxy so that the baseURL does not need to be updated every time
// Create an axios instance, initially using the default port
const axiosInstance = axios.create({
  baseURL: 'http://127.0.0.1:8000', // Default port, will be updated at runtime
  timeout: 10000,
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
      if (port && port !== 8000) {
        updateBaseURL(port)
      }
    })
    .catch((error) => {
      console.warn('Failed to get backend port, using default 8000:', error)
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
