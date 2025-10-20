import { useState, useEffect, useRef } from 'react'
import { useMemoizedFn } from 'ahooks'
import { Activity } from '../screen-monitor'
import { getLogger } from '@shared/logger/renderer'
import dayjs from 'dayjs'

const logger = getLogger('useActivityPolling')
export const useActivityPolling = (
  currentDate: Date,
  getActivitiesByDate: (date: Date) => Promise<any[]>,
  getNewActivities: (lastTime: string) => Promise<any[]>
) => {
  const [activities, setActivities] = useState<Activity[]>([])
  const activityPollingRef = useRef<NodeJS.Timeout | null>(null)
  const lastCheckedTimeRef = useRef<string>(dayjs().toISOString())

  // Determine if currently viewing today
  const isToday = dayjs(currentDate).isSame(dayjs(), 'day')

  // Initialize activities for current date
  useEffect(() => {
    const initActivities = async () => {
      const date = dayjs(currentDate).startOf('day').toDate()
      const todayActivities = await getActivitiesByDate(date)
      const todayActivitiesParsed: Activity[] = todayActivities.map((item: any) => ({
        ...item,
        resources: JSON.parse(item.resources)
      }))
      const uniqueActivities = Array.from(new Map(todayActivitiesParsed.map((item) => [item.id, item])).values())
      setActivities(uniqueActivities)

      // Update last checked time
      if (uniqueActivities.length > 0) {
        const latestActivity = uniqueActivities[uniqueActivities.length - 1]
        lastCheckedTimeRef.current = latestActivity.end_time || latestActivity.start_time
      } else {
        // If there are no activities, reset to the start of the day
        lastCheckedTimeRef.current = dayjs(currentDate).startOf('day').toISOString()
      }
    }
    initActivities()
  }, [currentDate, getActivitiesByDate])

  // Start polling for new activities
  const startActivityPolling = useMemoizedFn(() => {
    if (activityPollingRef.current) {
      clearInterval(activityPollingRef.current)
    }
    // Check new activities immediately
    const checkNewActivities = async () => {
      try {
        // Only poll for new activities when viewing today
        if (!isToday) {
          return
        }

        const newActivities = await getNewActivities(lastCheckedTimeRef.current)
        const newActivitiesParsed: Activity[] = newActivities.map((item: any) => ({
          ...item,
          resources: JSON.parse(item.resources)
        }))
        if (newActivitiesParsed && newActivitiesParsed.length > 0) {
          // Filter activities for the current date
          const currentDateStr = dayjs(currentDate).format('YYYY-MM-DD')
          const filteredActivities = newActivitiesParsed.filter((activity) => {
            const activityDateStr = dayjs(activity.start_time).format('YYYY-MM-DD')
            return activityDateStr === currentDateStr
          })

          if (filteredActivities.length > 0) {
            // Update last checked time to latest activity start time
            const latestActivity = filteredActivities[filteredActivities.length - 1]
            lastCheckedTimeRef.current = latestActivity.start_time
            // Add new activities to beginning of array (maintain time order) and deduplicate
            setActivities((prev) => {
              const existingIds = new Set(prev.map((a) => a.id))
              const uniqueNewActivities = filteredActivities.filter((a) => !existingIds.has(a.id))
              return [...uniqueNewActivities, ...prev]
            })
          }
        }
      } catch (error) {
        logger.error('Failed to check new activity', { error })
      }
    }
    // Execute immediately
    checkNewActivities()
    // Set timer
    activityPollingRef.current = setInterval(checkNewActivities, 5000) // Poll every 5 seconds
  })

  // Stop polling for new activities
  const stopActivityPolling = useMemoizedFn(() => {
    if (activityPollingRef.current) {
      clearInterval(activityPollingRef.current)
      activityPollingRef.current = null
    }
  })

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      stopActivityPolling()
    }
  }, [stopActivityPolling])

  return {
    activities,
    startActivityPolling,
    stopActivityPolling
  }
}
