import React from 'react'
import { useTranslation } from 'react-i18next'
import { Typography, Button } from '@arco-design/web-react'
import Stopped from '@renderer/assets/images/screen-monitor/stopped.png'
import NeedPermission from '@renderer/assets/images/screen-monitor/need-permission.svg'
import screenMonitorEmpty from '@renderer/assets/images/screen-monitor/screen-monitor-empty.svg'
import { SCREEN_INTERVAL_TIME } from '../constant'

const { Text } = Typography

interface EmptyStatePlaceholderProps {
  hasPermission: boolean
  isToday: boolean
  onGrantPermission: () => void
}

const EmptyStatePlaceholder: React.FC<EmptyStatePlaceholderProps> = ({ hasPermission, isToday, onGrantPermission }) => {
  const { t } = useTranslation()
  return (
    <div className="flex items-center justify-center flex-1 min-h-[300px]">
      <div className="text-center flex flex-col items-center justify-center">
        {hasPermission ? (
          isToday ? (
            <>
              <img src={Stopped} alt="Screen recording" style={{ width: 66, height: 78 }} />
              <Text style={{ marginTop: 16, width: 270, color: '#6C7191', fontSize: 12 }}>
                {t(
                  'screen_monitor.empty.start_recording_hint',
                  'Start screen recording, and then it will take screenshots and summarize your work records every {{interval}} minutes',
                  { interval: SCREEN_INTERVAL_TIME }
                )}
              </Text>
            </>
          ) : (
            <>
              <img src={screenMonitorEmpty} alt="Screen recording" style={{ width: 66, height: 78 }} />
              <Text style={{ marginTop: 16, width: 270, color: '#6C7191', fontSize: 12 }}>
                {t('common.no_data', 'No data available')}
              </Text>
            </>
          )
        ) : (
          <>
            <img src={NeedPermission} alt="Need permission" style={{ width: 286, height: 168, marginLeft: 67 }} />
            <Text style={{ marginTop: 16, width: 440, color: '#6C7191', fontSize: 12 }}>
              {t(
                'screen_monitor.empty.enable_permission_hint',
                'Enable screen recording permission, summary with AI every {{interval}} minutes',
                { interval: SCREEN_INTERVAL_TIME }
              )}
            </Text>
            <Button
              type="primary"
              size="large"
              onClick={onGrantPermission}
              className="[&_.arco-btn-primary]: !mt-6 [&_.arco-btn-primary]: !font-medium [&_.arco-btn-primary]: !bg-black">
              {t('screen_monitor.empty.enable_permission_btn', 'Enable Permission')}
            </Button>
          </>
        )}
      </div>
    </div>
  )
}

export default EmptyStatePlaceholder
