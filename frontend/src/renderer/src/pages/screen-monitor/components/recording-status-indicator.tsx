import React from 'react'
import { useTranslation } from 'react-i18next'
import { Typography } from '@arco-design/web-react'
import { SCREEN_INTERVAL_TIME } from '../constant'

const { Text } = Typography

interface RecordingStatusIndicatorProps {
  isMonitoring: boolean
  canRecord: boolean
  isToday: boolean
}

const RecordingStatusIndicator: React.FC<RecordingStatusIndicatorProps> = ({ isMonitoring, canRecord, isToday }) => {
  const { t } = useTranslation()
  if (!isToday) return null

  return (
    <>
      {isMonitoring ? (
        canRecord ? (
          <div className="w-full text-sm">
            <Text className="[&_.arco-typography]: !font-bold [&_.arco-typography]: !text-[#5252FF] [&_.arco-typography]: !text-xs">
              {t('screen_monitor.status.recording_screen', 'Recording screen...')}
            </Text>
            <div className="text-[#C9C9D4]">
              {t(
                'screen_monitor.status.recording_description',
                'Every {{interval}} minutes, MineContext generates an Activity based on screen analysis.',
                { interval: SCREEN_INTERVAL_TIME }
              )}
            </div>
          </div>
        ) : (
          <div className="w-full text-sm">
            <Text className="[&_.arco-typography]: !font-bold [&_.arco-typography]: !text-[#FF4D4F] [&_.arco-typography]: !text-xs">
              {t('screen_monitor.status.recording_stopped', 'Recording stopped')}
            </Text>
            <div className="text-[#C9C9D4]">
              {t(
                'screen_monitor.status.not_in_hours',
                "It's not in recording hours now. Recording will automatically start at the next allowed time."
              )}
            </div>
          </div>
        )
      ) : (
        <div style={{ width: '100%', fontSize: 14 }}>
          <Text style={{ fontWeight: 'bold', color: '#FF4D4F', fontSize: 12 }}>
            {t('screen_monitor.status.recording_stopped', 'Recording stopped')}
          </Text>
          <div style={{ color: '#C9C9D4' }}>
            {t('screen_monitor.status.can_start_again', 'You can start recording again')}
          </div>
        </div>
      )}
    </>
  )
}

export default RecordingStatusIndicator
