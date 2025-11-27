// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useEffect, useRef } from 'react'
import store, { persistor } from '@renderer/store'
import { Provider } from 'react-redux'
import { PersistGate } from 'redux-persist/integration/react'

import { ConfigProvider } from '@arco-design/web-react'
import enUS from '@arco-design/web-react/es/locale/en-US'
import zhCN from '@arco-design/web-react/es/locale/zh-CN'
import '@renderer/assets/main.css'
import '@renderer/assets/theme/index.less'
import 'allotment/dist/style.css'
import LoadingComponent from './components/Loading'
import { NotificationProvider } from './context/NotificationProvider'
import Router from './Router'
import { BackendStatus } from './components/Loading'
import { CaptureSourcesProvider } from './atom/capture.atom'
import Settings from './pages/settings/settings'
import { ServiceProvider, useObservableTask } from './atom/event-loop.atom'
import { getLogger } from '@shared/logger/renderer'
import { useMemoizedFn } from 'ahooks'

const logger = getLogger('App.tsx')
const isEnglish = true // Hardcode for now, will change later
interface BackendStatusInfo {
  status: BackendStatus
  port: number
  timestamp: string
}

function AppContent(): React.ReactElement {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('starting')
  const [showSetting, setShowSettings] = useState<boolean>(true)

  const checkInitialStatus = useMemoizedFn(async () => {
    try {
      const statusInfo: BackendStatusInfo = await window.electron.ipcRenderer.invoke('backend:get-status')
      setBackendStatus(statusInfo.status)
    } catch (error) {
      logger.error('Failed to get initial backend status:', { error })
      setBackendStatus('error')
    }
  })
  const statusCheckIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const clearStatusCheckInterval = useMemoizedFn(() => {
    if (statusCheckIntervalRef.current) {
      clearTimeout(statusCheckIntervalRef.current)
      statusCheckIntervalRef.current = null
    }
  })
  const scheduleNextCheck = useMemoizedFn(() => {
    statusCheckIntervalRef.current = setTimeout(() => {
      if (backendStatus !== 'running') {
        checkInitialStatus()
      } else {
        clearStatusCheckInterval()
      }
      scheduleNextCheck()
    }, 3000)
  })
  useEffect(() => {
    const handleStatusChange = (_event: any, statusInfo: BackendStatusInfo) => {
      logger.info('Backend status changed:', statusInfo)
      setBackendStatus(statusInfo.status)
      if (statusInfo.status === 'running') {
        clearStatusCheckInterval()
      }
    }

    checkInitialStatus()
    // Listen for status change events
    window.electron.ipcRenderer.on('backend:status-changed', handleStatusChange)

    scheduleNextCheck()

    return () => {
      clearStatusCheckInterval()
      window.electron.ipcRenderer.removeAllListeners('backend:status-changed')
    }
  }, [])

  useObservableTask({
    active: () => {
      logger.info('🔓 Screen unlocked, check backend sever initial status')
      checkInitialStatus()
    },
    inactive: () => {
      logger.info('🔒 Screen locked, stop check backend sever initial status')
      clearStatusCheckInterval()
    }
  })

  useEffect(() => {
    window.serverPushAPI.getInitCheckData((data) => {
      const temp = JSON.parse(data)
      logger.info('Init settings data:', temp)
      setShowSettings(!temp.data.components.llm)
    })
  }, [])

  // Decide whether to display the application based on the status
  const pythonServerStarted = backendStatus === 'running'
  const closeSetting = useMemoizedFn(() => {
    setShowSettings(false)
  })
  return (
    <>
      {pythonServerStarted ? (
        <CaptureSourcesProvider>
          {showSetting ? <Settings closeSetting={closeSetting} init /> : <Router />}
        </CaptureSourcesProvider>
      ) : (
        <LoadingComponent backendStatus={backendStatus} />
      )}
    </>
  )
}

function App(): React.ReactElement {
  return (
    <Provider store={store}>
      <ConfigProvider locale={isEnglish ? enUS : zhCN}>
        <ServiceProvider>
          <NotificationProvider>
            <PersistGate loading={null} persistor={persistor}>
              <AppContent />
            </PersistGate>
          </NotificationProvider>
        </ServiceProvider>
      </ConfigProvider>
    </Provider>
  )
}

export default App
