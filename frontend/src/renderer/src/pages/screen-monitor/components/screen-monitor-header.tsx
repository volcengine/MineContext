import React from 'react'
import { Button, Space, Typography, Popover } from '@arco-design/web-react'
import { IconPlayArrow, IconSettings, IconRecordStop, IconVideoCamera } from '@arco-design/web-react/icon'

const { Title, Text } = Typography

interface ScreenMonitorHeaderProps {
  hasPermission: boolean
  isMonitoring: boolean
  isToday: boolean
  screenAllSources: any[]
  appAllSources: any[]
  onOpenSettings: () => void
  onStartMonitoring: () => void
  onStopMonitoring: () => void
  onRequestPermission: () => void
}

const ScreenMonitorHeader: React.FC<ScreenMonitorHeaderProps> = ({
  hasPermission,
  isMonitoring,
  isToday,
  screenAllSources,
  appAllSources,
  onOpenSettings,
  onStartMonitoring,
  onStopMonitoring,
  onRequestPermission
}) => {
  return (
    <div className="flex justify-between items-start mb-3 flex-col md:flex-row">
      <div className="w-full md:w-4/5">
        <Title
          heading={3}
          className="[&_.arco-typography]: !mt-1 [&_.arco-typography]: !font-bold [&_.arco-typography]: !text-[24px] [&_.arco-typography]: !text-black">
          Screen Monitor
        </Title>
        <Text type="secondary" className="[&_.arco-typography]: !text-[13px]">
          Screen Monitor captures anything on your screen and transforms it into intelligent, connected Contexts. All
          data stays local with full privacy protection ✨
        </Text>
      </div>
      <div className="flex items-center ml-0 md:ml-6 mt-4 md:mt-0 justify-end">
        {hasPermission ? (
          <Space>
            <Popover content="Settings can only be adjusted after Stop Recording." disabled={!isMonitoring}>
              <Button
                type="outline"
                icon={<IconSettings />}
                size="large"
                disabled={isMonitoring}
                onClick={onOpenSettings}
                className="[&_.arco-btn]: !bg-white [&_.arco-btn]: !border-gray-300 [&_.arco-btn]: !text-black [&_.arco-btn:hover]: !bg-gray-50">
                Settings
              </Button>
            </Popover>
            {!isMonitoring ? (
              <Popover
                content="Please click the settings button and select your monitoring window or screen."
                disabled={!(screenAllSources.length === 0 && appAllSources.length === 0)}>
                <Button
                  type="primary"
                  icon={<IconPlayArrow />}
                  size="large"
                  onClick={onStartMonitoring}
                  disabled={isMonitoring || !isToday}
                  style={{
                    background: '#000'
                  }}>
                  Start Recording
                </Button>
              </Popover>
            ) : (
              <Button
                type="primary"
                status="danger"
                icon={<IconRecordStop />}
                size="large"
                onClick={onStopMonitoring}
                className="[&_.arco-btn-primary]: !bg-red-500 [&_.arco-btn-primary:hover]: !bg-red-600">
                Stop Recording
              </Button>
            )}
          </Space>
        ) : (
          <Button
            type="primary"
            status="danger"
            icon={<IconVideoCamera />}
            size="large"
            onClick={onRequestPermission}
            className="[&_.arco-btn-primary]:!bg-red-500 [&_.arco-btn-primary:hover]:!bg-red-600">
            Request permission
          </Button>
        )}
      </div>
    </div>
  )
}

export default ScreenMonitorHeader
