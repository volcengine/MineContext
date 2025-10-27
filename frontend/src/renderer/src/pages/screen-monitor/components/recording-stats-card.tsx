import React from 'react'
import { Tooltip } from '@arco-design/web-react'

export interface RecordingStats {
  received_screenshots: number
  processing_screenshots: number
  processed_screenshots: number
  succeeded_screenshots: number
  failed_screenshots: number
  generated_activities: number
  next_activity_eta_seconds: number
  recent_errors: Array<{
    error_message: string
    processor_name: string
    timestamp: string
  }>
}

interface RecordingStatsCardProps {
  stats: RecordingStats | null
}

const RecordingStatsCard: React.FC<RecordingStatsCardProps> = ({ stats }) => {
  console.log('[RecordingStatsCard] Rendering with stats:', stats)

  if (!stats) {
    console.log('[RecordingStatsCard] Stats is null, not rendering')
    return null
  }

  console.log('[RecordingStatsCard] Using stats:', stats)

  return (
    <div className="mt-2 text-xs text-[#86909C]">
      <span>Received: </span>
      <span className="text-[#1D2129] font-medium">{stats.received_screenshots}</span>
      <span className="mx-2">•</span>
      <span>Processed: </span>
      <span className="text-[#00B42A] font-medium">{stats.succeeded_screenshots}</span>
      {stats.failed_screenshots > 0 && (
        <>
          <span className="mx-1">/</span>
          <Tooltip
            content={
              <div className="max-w-xs">
                <div className="font-medium mb-1">Recent Errors:</div>
                {stats.recent_errors.length > 0 ? (
                  <ul className="text-xs space-y-1">
                    {stats.recent_errors.map((error, index) => (
                      <li key={index} className="break-words">
                        {error.error_message}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <span className="text-xs">No detailed error information available</span>
                )}
              </div>
            }
          >
            <span className="text-[#FF4D4F] font-medium cursor-help">
              {stats.failed_screenshots} failed
            </span>
          </Tooltip>
        </>
      )}
    </div>
  )
}

export default RecordingStatsCard
