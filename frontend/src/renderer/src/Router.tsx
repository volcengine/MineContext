// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

// import '@renderer/databases'

import { FC, useEffect, useMemo } from 'react'
import { HashRouter, Route, Routes, useNavigate } from 'react-router-dom'

import HomePage from './pages/home/home-page'
import VaultPage from './pages/vault/Vault'
import ScreenMonitor from './pages/screen-monitor/screen-monitor'
import Settings from './pages/settings/settings'

import Files from './pages/files/Files'
import AIDemo from './pages/ai-demo/ai-demo'
import Sidebar from './components/Sidebar'
import 'allotment/dist/style.css'
import { useEvents } from './hooks/use-events'
import { useObservableTask } from './atom/event-loop.atom'
import { IpcServerPushChannel } from '@shared/ipc-server-push-channel'

const AppContent: FC = () => {
  const navigate = useNavigate()
  const { startPolling, stopPolling } = useEvents()
  useObservableTask({
    active: startPolling,
    inactive: stopPolling
  })

  // Listen for tray navigation event
  useEffect(() => {
    const handleNavigateToScreenMonitor = () => {
      navigate('/screen-monitor')
    }

    window.electron.ipcRenderer.on(IpcServerPushChannel.Tray_NavigateToScreenMonitor, handleNavigateToScreenMonitor)

    return () => {
      window.electron.ipcRenderer.removeListener(
        IpcServerPushChannel.Tray_NavigateToScreenMonitor,
        handleNavigateToScreenMonitor
      )
    }
  }, [navigate])

  // Global listener for tray toggle recording - navigate to screen-monitor and pass toggle signal
  useEffect(() => {
    const handleTrayToggleRecording = () => {
      // Navigate to screen-monitor page with state indicating recording should be toggled
      navigate('/screen-monitor', { state: { toggleRecording: true } })
    }

    window.electron.ipcRenderer.on(IpcServerPushChannel.Tray_ToggleRecording, handleTrayToggleRecording)

    return () => {
      window.electron.ipcRenderer.removeListener(IpcServerPushChannel.Tray_ToggleRecording, handleTrayToggleRecording)
    }
  }, [navigate])

  useEffect(() => {
    startPolling()

    return () => stopPolling()
  }, [])

  const routes = useMemo(() => {
    return (
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/vault" element={<VaultPage />} />
        <Route path="/screen-monitor" element={<ScreenMonitor />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/files" element={<Files />} />
        <Route path="/ai-demo" element={<AIDemo />} />
      </Routes>
    )
  }, [])

  return (
    <div
      className="flex h-screen"
      style={{
        height: '100vh',
        background:
          'linear-gradient(165.9deg, #CEC1D2 -3.95%, #D9DAE8 3.32%, #F2F2F2 23.35%, #F2F0E6 71.67%, #F9FAED 76.64%, #FFEDDF 83.97%)'
      }}>
      <div style={{ appRegion: 'drag', width: '12px', height: '100%' } as React.CSSProperties} />
      <Sidebar />
      <div className="flex-1 flex flex-col pr-2">{routes}</div>
    </div>
  )
}

const Router: FC = () => {
  return (
    <HashRouter>
      <AppContent />
    </HashRouter>
  )
}

export default Router
