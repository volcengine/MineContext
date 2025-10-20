// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { Layout } from '@arco-design/web-react'
import VaultTree from '@renderer/components/vault-tree'
import { useNavigation } from '@renderer/hooks/use-navigation'
import logo from '/src/assets/icons/logo.svg'
import homeIcon from '/src/assets/icons/home.svg'
import screenMonitorIcon from '/src/assets/icons/screen-monitor.svg'
import settings from '/src/assets/icons/settings.svg'

// import resourcesIcon from '/src/assets/icons/resources.svg'
// import { IconRobot } from '@arco-design/web-react/icon'
import './index.css'
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
      className="sidebar-container [&_.arco-layout-sider]: !flex !flex-col !bg-transparent !height-[100vh] !py-0 !pl-[12px] !py-[16px]">
      {/* Top logo and title */}
      <div className="flex items-center px-4 py-2 h-[80px] flex-shrink-0" onClick={() => handleTabChange('home')}>
        <div className="flex items-center gap-2 flex-1">
          <img
            src={logo}
            alt="Logo"
            style={{
              width: 24,
              height: 24
            }}
          />
          <div
            onClick={() => navigateToMainTab('home', '/')}
            className="text-base font-bold text-[#1d2129] m-0 whitespace-nowrap cursor-pointer">
            MineContext
          </div>
        </div>
      </div>

      {/* Tab navigation */}
      <div className="flex-shrink-0">
        {tabItems.map((item) => (
          <div
            key={item.key}
            onClick={() => handleTabChange(item.key)}
            className={`h-[28px] p-2 px-3 text-left cursor-pointer text-sm leading-[22px] 
              ${isMainTabActive(item.key) ? 'bg-[#FFFFFF66] font-medium' : 'bg-transparent font-normal hover:bg-[#FFFFFF66]'} 
              text-[#3F3F54] transition-all duration-200 ease-in-out rounded-lg flex items-center gap-2 mt-[5px]`}>
            <span className="flex">{item.icon}</span>
            {item.label}
          </div>
        ))}
      </div>

      <VaultTree />
    </Sider>
  )
}

export default Sidebar
