import React from 'react'
import { Typography, Timeline } from '@arco-design/web-react'
import { Activity } from '../screen-monitor'
import { ActivityTimelineItem } from './activitie-timeline-item'
import { formatTime } from '@renderer/utils/time'
import { SCREEN_INTERVAL_TIME } from '../constant'
import RecordingStatsCard, { RecordingStats } from './recording-stats-card'
import dayjs from 'dayjs'

const { Text } = Typography
const TimelineItem = Timeline.Item

interface RecordingTimelineProps {
  isMonitoring: boolean
  isToday: boolean
  canRecord: boolean
  activities: Activity[]
  recordingStats: RecordingStats | null
}

const RecordingTimeline: React.FC<RecordingTimelineProps> = ({
  isMonitoring,
  isToday,
  canRecord,
  activities,
  recordingStats
}) => {
  console.log('[RecordingTimeline] Props:', {
    isMonitoring,
    isToday,
    canRecord,
    hasRecordingStats: !!recordingStats,
    recordingStats
  })

  return (
    <div className="mt-5">
      <Timeline labelPosition="relative">
        {isToday && (
          <TimelineItem label="Now">
            {isMonitoring ? (
              canRecord ? (
                <>
                  <div className="w-full text-sm">
                    <Text className="[&_.arco-typography]: !font-bold [&_.arco-typography]: !text-[#5252FF] [&_.arco-typography]: !text-xs">
                      Recording screen...
                    </Text>
                    <div className="text-[#C9C9D4]">
                      Every {SCREEN_INTERVAL_TIME} minutes, MineContext generates an Activity based on screen
                      analysis.
                    </div>
                  </div>
                  {console.log('[RecordingTimeline] About to render RecordingStatsCard')}
                  <RecordingStatsCard stats={recordingStats} />
                </>
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
          </TimelineItem>
        )}

        {/* Display activities */}
        {activities
          .sort((a, b) => dayjs(b.start_time).valueOf() - dayjs(a.start_time).valueOf()) // Sort by time in descending order
          .map((activity) => (
            <TimelineItem label={formatTime(activity?.end_time)} key={activity.id}>
              <ActivityTimelineItem key={activity.id} activity={activity} />
            </TimelineItem>
          ))}
      </Timeline>
    </div>
  )
}

export default RecordingTimeline
