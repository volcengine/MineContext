// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useState } from 'react'
import { Typography, Space, Tabs, Alert, Button } from '@arco-design/web-react'
import AISidebar from '@renderer/components/ai-sidebar/index'

const { Title } = Typography
const TabPane = Tabs.TabPane

const AIDemo = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('demo')

  return (
    <div className="h-screen flex overflow-hidden">
      {/* Main content area */}
      <div
        className={`flex-1 h-full p-6 overflow-y-auto relative transition-[width] duration-300 ease-in-out ${isSidebarOpen ? 'w-[calc(100%-400px)]' : ''}`}>
        <div className="max-w-[1200px] mx-auto">
          <div className="text-center mb-12">
            <Title heading={1} style={{ marginBottom: '16px', color: '#1d2129' }}>
              AI Assistant Demo Page
            </Title>
          </div>

          <Tabs activeTab={activeTab} onChange={setActiveTab}>
            <TabPane key="demo" title="Function Demo">
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <Alert
                  type="info"
                  title="Get Started"
                  content="Please set your Doubao API key on the configuration page first, then click the AI button on the right to start a conversation!"
                  showIcon
                  style={{ marginBottom: '24px' }}
                />
              </Space>
            </TabPane>
          </Tabs>
        </div>

        {/* AI toggle button - positioned relative to the content area */}
        <Button
          onClick={() => setIsSidebarOpen(true)}
          className="absolute right-6 top-1/2 -translate-y-1/2 z-[100] hover:-translate-y-1/2 hover:scale-110 transition-transform duration-200 ease-in-out"></Button>
      </div>

      {/* AI sidebar - squeeze layout */}
      <div className="w-[400px] h-screen bg-white border-l border-gray-200 flex flex-col flex-shrink-0 shadow-[-2px_0_8px_rgba(0,0,0,0.1)]">
        <AISidebar />
      </div>
    </div>
  )
}

export default AIDemo
