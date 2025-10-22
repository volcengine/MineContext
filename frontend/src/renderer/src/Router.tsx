// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

// import '@renderer/databases'

import { FC, useEffect, useMemo } from 'react'
import { HashRouter, Route, Routes } from 'react-router-dom'

import HomePage from './pages/home/home-page'
import VaultPage from './pages/vault/Vault'
import ScreenMonitor from './pages/screen-monitor/screen-monitor'
import Settings from './pages/settings/settings'

import Files from './pages/files/Files'
import AIDemo from './pages/ai-demo/ai-demo'
import Sidebar from './components/Sidebar'
import 'allotment/dist/style.css'
import { useEvents } from './hooks/use-events'
import GlobalEventService from './services/GlobalEventService'
import { useServiceHandler } from './atom/event-loop.atom'

const Router: FC = () => {
  const { startPolling, stopPolling } = useEvents()
  const eventService = GlobalEventService.getInstance()

  // Listen for screen lock events to adjust polling frequency
  useServiceHandler('lock-screen', () => {
    eventService.setLocked(true)
  })

  useServiceHandler('unlock-screen', () => {
    eventService.setLocked(false)
  })

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
    <HashRouter>
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
    </HashRouter>
  )
}

export default Router
