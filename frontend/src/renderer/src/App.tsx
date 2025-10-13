// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useEffect } from 'react'
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
import { ServiceProvider, useServiceHandler } from './atom/event-loop.atom'
import { getLogger } from '@shared/logger/renderer'

const logger = getLogger('App.tsx')
const isEnglish = true // 先写死，后面再改
interface BackendStatusInfo {
  status: BackendStatus
  port: number
  timestamp: string
}

function AppContent(): React.ReactElement {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('starting')
  const [showSetting, setShowSettings] = useState<boolean>(false)
  const isScreenLockedRef = React.useRef(false)

  useEffect(() => {
    let statusCheckInterval: NodeJS.Timeout
    // 获取初始状态
    const checkInitialStatus = async () => {
      try {
        const statusInfo: BackendStatusInfo = await window.electron.ipcRenderer.invoke('backend:get-status')
        setBackendStatus(statusInfo.status)
      } catch (error) {
        logger.error('Failed to get initial backend status:', { error })
        setBackendStatus('error')
      }
    }

    // 监听状态变化
    const handleStatusChange = (_event: any, statusInfo: BackendStatusInfo) => {
      logger.info('Backend status changed:', statusInfo)
      setBackendStatus(statusInfo.status)
    }

    checkInitialStatus()

    // 监听状态变化事件
    window.electron.ipcRenderer.on('backend:status-changed', handleStatusChange)

    // 定期检查状态（作为备用）
    // 动态调整检查间隔：锁屏时降低频率
    const getCheckInterval = () => (isScreenLockedRef.current ? 30000 : 3000) // 锁屏时30秒，正常时3秒

    const scheduleNextCheck = () => {
      statusCheckInterval = setTimeout(() => {
        if (backendStatus !== 'running') {
          checkInitialStatus()
        }
        scheduleNextCheck()
      }, getCheckInterval())
    }

    scheduleNextCheck()

    return () => {
      if (statusCheckInterval) {
        clearTimeout(statusCheckInterval)
      }
      window.electron.ipcRenderer.removeAllListeners('backend:status-changed')
    }
  }, [backendStatus])

  // 监听锁屏/解锁事件
  useServiceHandler('lock-screen', () => {
    logger.info('🔒 Screen locked, reducing backend status check frequency')
    isScreenLockedRef.current = true
  })

  useServiceHandler('unlock-screen', () => {
    logger.info('🔓 Screen unlocked, restoring backend status check frequency')
    isScreenLockedRef.current = false
  })

  useEffect(() => {
    window.serverPushAPI.getInitCheckData((data) => {
      const temp = JSON.parse(data)

      setShowSettings(!temp.data.components.llm)
    })
  }, [])

  // 根据状态决定是否显示应用
  const pythonServerStarted = backendStatus === 'running'

  return (
    <>
      {pythonServerStarted ? (
        <CaptureSourcesProvider>
          {showSetting ? (
            <Settings
              onOk={() => {
                setShowSettings(false)
              }}
            />
          ) : (
            <Router />
          )}
        </CaptureSourcesProvider>
      ) : (
        <LoadingComponent backendStatus={backendStatus} />
      )}
    </>
  )
}

function App(): React.ReactElement {
  logger.info('App initialized')

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
