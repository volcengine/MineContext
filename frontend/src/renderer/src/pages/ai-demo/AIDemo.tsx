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
        {/* 主内容区域 */}
        <div className={`ai-demo-content ${isSidebarOpen ? 'sidebar-open' : ''}`}>
          <div className="ai-demo-main">
            <div className="ai-demo-header">
              <Title heading={1} style={{ marginBottom: '16px', color: '#1d2129' }}>
                AI助手演示页面
              </Title>
            </div>

            <Tabs activeTab={activeTab} onChange={setActiveTab}>
              <TabPane key="demo" title="功能演示">
                <Space direction="vertical" size="large" style={{ width: '100%' }}>
                  <Alert
                    type="info"
                    title="开始使用"
                    content="请先在配置页面设置您的豆包API密钥，然后点击右侧AI按钮开始对话！"
                    showIcon
                    style={{ marginBottom: '24px' }}
                  />

                </Space>
              </TabPane>


            </Tabs>
          </div>

          {/* AI切换按钮 - 相对于内容区域定位 */}
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

        {/* AI侧边栏 - 挤压式布局 */}
        <AISidebar />
      </div>
  )
}

export default AIDemo
