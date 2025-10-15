import React from 'react'
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

const EmptyStatePlaceholder: React.FC<EmptyStatePlaceholderProps> = ({
  hasPermission,
  isToday,
  onGrantPermission
}) => {
  return (
    <div className="recording-area-content">
      <div className="recording-placeholder">
        {hasPermission ? (
          isToday ? (
            <>
              <img src={Stopped} alt="Screen recording" style={{ width: 66, height: 78 }} />
              <Text style={{ marginTop: 16, width: 270, color: '#6C7191', fontSize: 12 }}>
                Start screen recording, and then it will take screenshots and summarize your work records
                every {SCREEN_INTERVAL_TIME} minutes
              </Text>
            </>
          ) : (
            <>
              <img src={screenMonitorEmpty} alt="Screen recording" style={{ width: 66, height: 78 }} />
              <Text style={{ marginTop: 16, width: 270, color: '#6C7191', fontSize: 12 }}>
                No data available
              </Text>
            </>
          )
        ) : (
          <>
            <img
              src={NeedPermission}
              alt="Need permission"
              style={{ width: 286, height: 168, marginLeft: 67 }}
            />
            <Text style={{ marginTop: 16, width: 440, color: '#6C7191', fontSize: 12 }}>
              Enable screen recording permission, summary with AI every {SCREEN_INTERVAL_TIME} minutes
            </Text>
            <Button
              type="primary"
              size="large"
              onClick={onGrantPermission}
              className="[&_.arco-btn-primary]:!mt-6 [&_.arco-btn-primary]:!font-medium [&_.arco-btn-primary]:!bg-black">
              Enable Permission
            </Button>
          </>
        )}
      </div>
    </div>
  )
}

export default EmptyStatePlaceholder