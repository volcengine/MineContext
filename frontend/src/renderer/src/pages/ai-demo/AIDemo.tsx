// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useState } from 'react'
import { Typography, Space, Tabs, Alert, Button } from '@arco-design/web-react'
import AISidebar from '@renderer/components/AISidebar/index'
import './AIDemo.css'

const { Title } = Typography
const TabPane = Tabs.TabPane

const AIDemo = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('demo')



    return (
      <div className="ai-demo-container">
        {/* Main content area */}
        <div className={`ai-demo-content ${isSidebarOpen ? 'sidebar-open' : ''}`}>
          <div className="ai-demo-main">
            <div className="ai-demo-header">
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
            style={{
              position: 'absolute',
              right: '24px',
              top: '50%',
              transform: 'translateY(-50%)',
              zIndex: 100,
            }}
          >
          </Button>
        </div>

        {/* AI sidebar - squeeze layout */}
        <AISidebar />
      </div>
  )
}

export default AIDemo
