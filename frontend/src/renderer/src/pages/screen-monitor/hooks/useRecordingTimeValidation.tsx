import { useState, useEffect } from 'react'
import { useMemoizedFn } from 'ahooks'
export const useRecordingTimeValidation = (
    enableRecordingHours: boolean,
    recordingHours: [string, string],
    applyToDays: 'weekday' | 'everyday',
    isMonitoring: boolean) => {
  const [canRecord, setCanRecord] = useState(false)

  const checkCanRecord = useMemoizedFn(() => {
  if (enableRecordingHours) {
        const currentDay = new Date().getDay()
        const currentHour = new Date().getHours()
        const currentMinute = new Date().getMinutes()

  // Check if within allowed date range
        if (applyToDays === 'weekday') {
          // 0 = Sunday, 6 = Saturday, 1-5 = Monday-Friday
          if (currentDay === 0 || currentDay === 6) {
            setCanRecord(false)
            return false
          }
        }

  //       // Check if within allowed time range
        if (recordingHours && recordingHours.length === 2) {
          const [startTime, endTime] = recordingHours
          const [startHour, startMinute] = startTime.split(':').map(Number)
          const [endHour, endMinute] = endTime.split(':').map(Number)
          const currentTotalMinutes = currentHour * 60 + currentMinute
          const startTotalMinutes = startHour * 60 + startMinute
          const endTotalMinutes = endHour * 60 + endMinute

          // If end time is less than start time, it crosses midnight
          if (endTotalMinutes < startTotalMinutes) {
            // Current time is after start time or before end time
            const result = currentTotalMinutes >= startTotalMinutes || currentTotalMinutes <= endTotalMinutes
            setCanRecord(result)
            return result
          } else {
            // Normal time range
            const result = currentTotalMinutes >= startTotalMinutes && currentTotalMinutes <= endTotalMinutes
            setCanRecord(result)
            return result
          }
        }
      }
      setCanRecord(true)
      return true
    })
  //
  //   // Check recording status on mount
    useEffect(() => {
      checkCanRecord()
    }, [checkCanRecord])
  //   // Periodically check recording status
    useEffect(() => {
      let interval: NodeJS.Timeout | null = null
      if (isMonitoring && enableRecordingHours) {
        interval = setInterval(() => {
          checkCanRecord()
        }, 60000) // Check every minute
      }
      return () => {
        if (interval) {
          clearInterval(interval)
        }
      }
    }, [isMonitoring, enableRecordingHours, checkCanRecord])

    return { canRecord, checkCanRecord }
}
