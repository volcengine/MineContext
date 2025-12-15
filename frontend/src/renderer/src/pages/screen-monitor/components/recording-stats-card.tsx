import React from 'react'
import { useTranslation } from 'react-i18next'
import { Tooltip, Image } from '@arco-design/web-react'
import { pathToFileURL } from '@renderer/utils/file'

export interface RecordingStats {
  processed_screenshots: number
  failed_screenshots: number
  generated_activities: number
  next_activity_eta_seconds: number
  recent_errors: Array<{
    error_message: string
    processor_name: string
    timestamp: string
  }>
  recent_screenshots: string[]
}

interface RecordingStatsCardProps {
  stats: RecordingStats | null
}

const RecordingStatsCard: React.FC<RecordingStatsCardProps> = ({ stats }) => {
  const { t } = useTranslation()

  if (!stats) {
    return null
  }

  return (
    <div className="mt-2">
      {/* Recent screenshots display */}
      {stats.recent_screenshots && stats.recent_screenshots.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2">
          <Image.PreviewGroup infinite className="[&_.arco-image-preview-img]:!scale-80">
            {stats.recent_screenshots.map((path, index) => (
              <Image
                key={index}
                src={pathToFileURL(path)}
                width={110}
                height={60}
                alt={`screenshot-${index + 1}`}
                className="cursor-pointer rounded-[8px] overflow-hidden"
              />
            ))}
          </Image.PreviewGroup>
        </div>
      )}

      {/* Stats text */}
      <div className="text-xs text-[#86909C]">
        <span className="text-[#00B42A] font-medium">{stats.processed_screenshots}</span>
        <span>
          {' '}
          {t('screen_monitor.stats.screenshots_processed', 'screenshot{{s}} processed', {
            s: stats.processed_screenshots !== 1 ? 's' : ''
          })}
        </span>
        {stats.failed_screenshots > 0 && (
          <>
            <span className="mx-2">•</span>
            <Tooltip
              content={
                <div className="max-w-xs">
                  <div className="font-medium mb-1">{t('screen_monitor.stats.recent_errors', 'Recent Errors:')}</div>
                  {stats.recent_errors.length > 0 ? (
                    <ul className="text-xs space-y-1">
                      {stats.recent_errors.map((error, index) => (
                        <li key={index} className="break-words">
                          {error.error_message}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-xs">
                      {t('screen_monitor.stats.no_error_info', 'No detailed error information available')}
                    </span>
                  )}
                </div>
              }>
              <span className="text-[#FF4D4F] font-medium cursor-help underline decoration-dashed">
                {stats.failed_screenshots}{' '}
                {t('screen_monitor.stats.screenshots_failed', 'screenshot{{s}} failed', {
                  s: stats.failed_screenshots > 1 ? 's' : ''
                })}
              </span>
            </Tooltip>
          </>
        )}
      </div>
    </div>
  )
}

export default RecordingStatsCard
