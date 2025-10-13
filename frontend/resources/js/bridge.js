// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

;(() => {
  let messageId = 0
  const pendingCalls = new Map()

  function api(method, ...args) {
    const id = messageId++
    return new Promise((resolve, reject) => {
      pendingCalls.set(id, { resolve, reject })
      window.parent.postMessage({ id, type: 'api-call', method, args }, '*')
    })
  }

  window.addEventListener('message', (event) => {
    if (event.data.type === 'api-response') {
      const { id, result, error } = event.data
      const pendingCall = pendingCalls.get(id)
      if (pendingCall) {
        if (error) {
          pendingCall.reject(new Error(error))
        } else {
          pendingCall.resolve(result)
        }
        pendingCalls.delete(id)
      }
    }
  })

  window.api = new Proxy(
    {},
    {
      get: (target, prop) => {
        return (...args) => api(prop, ...args)
      }
    }
  )
})()
