// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { Layout, Typography } from '@arco-design/web-react'
import VaultTree from '@renderer/components/VaultTree'
import { useNavigation } from '@renderer/hooks/useNavigation'
import logo from '/src/assets/icons/logo.svg'
import homeIcon from '/src/assets/icons/home.svg'
import screenMonitorIcon from '/src/assets/icons/screen-monitor.svg'
import settings from '/src/assets/icons/settings.svg'

// import resourcesIcon from '/src/assets/icons/resources.svg'
// import { IconRobot } from '@arco-design/web-react/icon'
import './index.css'

const { Text } = Typography
const { Sider } = Layout

const tabItems = [
  {
    key: 'home',
    icon: <img src={homeIcon} alt="home" style={{ width: 15, height: 15 }} />,
    label: 'Home',
    path: '/'
  },
  // {
  //   key: 'ai-demo',
  //   icon: <IconRobot style={{ width: 16, height: 16 }} />,
  //   label: 'AI Demo',
  //   path: '/ai-demo'
  // },
  {
    key: 'screen-monitor',
    icon: <img src={screenMonitorIcon} alt="screen-monitor" style={{ width: 15, height: 15 }} />,
    label: 'Screen Monitor',
    path: '/screen-monitor'
  },
  {
    key: 'settings',
    icon: <img src={settings} alt="settings" style={{ width: 15, height: 15 }} />,
    label: 'Settings',
    path: '/settings'
  }
  // {
  //   key: 'files',
  //   icon: <img src={resourcesIcon} alt="resources" style={{ width: 15, height: 15 }} />,
  //   label: 'Resources',
  //   path: '/files'
  // },
]

const Sidebar = () => {
  const { navigateToMainTab, isMainTabActive } = useNavigation()

  const handleTabChange = (key: string) => {
    const item = tabItems.find((item) => item.key === key)
    if (item) {
      navigateToMainTab(key, item.path)
    }
  }

  return (
    <Sider
      width={176}
      className="sidebar-container"
      style={{
        background: 'transparent',
        // borderRight: '1px solid #e5e6eb',
        height: '100vh',
        padding: '0 12px 16px',
        display: 'flex',
        flexDirection: 'column'
      }}>
      {/* Top logo and title */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '8px 16px',
          height: '80px',
          flexShrink: 0
        }}
        onClick={() => handleTabChange('home')}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            flex: 1
          }}>
          <img
            src={logo}
            alt="Logo"
            style={{
              width: 24,
              height: 24
            }}
          />
          <Text
            style={{
              fontSize: 16,
              fontWeight: 700,
              color: '#1d2129',
              margin: 0,
              whiteSpace: 'nowrap'
            }}
            onClick={() => navigateToMainTab('home', '/')}
            className="cursor-pointer">
            MineContext
          </Text>
        </div>
      </div>

      {/* Tab navigation */}
      <div
        style={{
          flexShrink: 0
        }}>
        {tabItems.map((item) => (
          <div
            key={item.key}
            onClick={() => handleTabChange(item.key)}
            className="h-[28px]"
            style={{
              padding: '8px 12px',
              textAlign: 'left',
              cursor: 'pointer',
              backgroundColor: isMainTabActive(item.key) ? '#FFFFFF66' : 'transparent',
              fontSize: '13px',
              lineHeight: '22px',
              color: '#3F3F54',
              fontWeight: isMainTabActive(item.key) ? 500 : 400,
              transition: 'all 0.2s ease',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              marginTop: 5
            }}
            onMouseEnter={(e) => {
              if (!isMainTabActive(item.key)) {
                e.currentTarget.style.backgroundColor = '#FFFFFF66'
              }
            }}
            onMouseLeave={(e) => {
              if (!isMainTabActive(item.key)) {
                e.currentTarget.style.backgroundColor = 'transparent'
              }
            }}>
            <span style={{ display: 'flex' }}>{item.icon}</span>
            {item.label}
          </div>
        ))}
      </div>

      <VaultTree />
    </Sider>
  )
}

export default Sidebar
