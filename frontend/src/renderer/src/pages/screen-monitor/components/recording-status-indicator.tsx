import React from 'react'
import { Typography } from '@arco-design/web-react'
import { SCREEN_INTERVAL_TIME } from '../constant'

const { Text } = Typography

interface RecordingStatusIndicatorProps {
  isMonitoring: boolean
  canRecord: boolean
  isToday: boolean
}

const RecordingStatusIndicator: React.FC<RecordingStatusIndicatorProps> = ({ isMonitoring, canRecord, isToday }) => {
  if (!isToday) return null

  return (
    <>
      {isMonitoring ? (
        canRecord ? (
          <div className="w-full text-sm">
            <Text className="[&_.arco-typography]: !font-bold [&_.arco-typography]: !text-[#5252FF] [&_.arco-typography]: !text-xs">
              Recording screen...
            </Text>
            <div className="text-[#C9C9D4]">
              Every {SCREEN_INTERVAL_TIME} minutes, MineContext generates an Activity based on screen analysis.
            </div>
          </div>
        ) : (
          <div className="w-full text-sm">
            <Text className="[&_.arco-typography]: !font-bold [&_.arco-typography]: !text-[#FF4D4F] [&_.arco-typography]: !text-xs">
              Recording stopped
            </Text>
            <div className="text-[#C9C9D4]">
              It's not in recording hours now. Recording will automatically start at the next allowed time.
            </div>
          </div>
        )
      ) : (
        <div style={{ width: '100%', fontSize: 14 }}>
          <Text style={{ fontWeight: 'bold', color: '#FF4D4F', fontSize: 12 }}>Recording stopped</Text>
          <div style={{ color: '#C9C9D4' }}>You can start recording again</div>
        </div>
      )}
    </>
  )
}

export default RecordingStatusIndicator
