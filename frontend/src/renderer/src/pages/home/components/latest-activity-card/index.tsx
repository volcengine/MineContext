// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useNavigation } from '@renderer/hooks/use-navigation'
import { FC, useState } from 'react'
import { CardLayout } from '../layout'
import { useMount, useUnmount } from 'ahooks'
import { ActivityTimelineItem } from '@renderer/pages/screen-monitor/components/activitie-timeline-item'
import { isEmpty } from 'lodash'
import dayjs from 'dayjs'
// import { useServiceHandler } from '@renderer/atom/event-loop.atom'
// import { POWER_MONITOR_KEY } from '@shared/constant/power-monitor'

interface LatestActivityCardProps {
  title: string
  hasToDocButton?: boolean
  emptyText?: string
  children?: React.ReactNode
}

// const NORMAL_INTERVAL = 60000 // Normal: 60 seconds
// const LOCKED_INTERVAL = 300000 // Locked: 5 minutes

const LatestActivityCard: FC<LatestActivityCardProps> = () => {
  const { navigateToMainTab } = useNavigation()

  // Store polling timer ID
  // const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)
  // const isLockedRef = useRef(false)

  const handleNavigateToScreenMonitor = () => {
    navigateToMainTab('screen-monitor', '/screen-monitor')
  }

  // const { run: getLatestActivity, data } = useRequest<Activity, any>(async () => {
  //   const res = await window.dbAPI.getLatestActivity()
  //   return res as Activity
  // })
  const [latestActivity, setLatestActivity] = useState<Activity>()
  useMount(() => {
    window.eventLoop.getHomeLatestActivity('running')
    window.serverPushAPI.pushHomeLatestActivity((data) => {
      console.log('总耗时 --->', dayjs().format('YYYY-MM-DD HH:mm:ss'))

      setLatestActivity(data)
    })
  })
  useUnmount(() => {
    window.eventLoop.getHomeLatestActivity('stopped')
  })

  // const startPolling = (interval: number) => {
  //   if (pollIntervalRef.current) {
  //     clearInterval(pollIntervalRef.current)
  //   }
  //   pollIntervalRef.current = setInterval(() => {
  //     getLatestActivity()
  //   }, interval)
  //   console.log('LatestActivityCard: Polling started with interval:', interval)
  // }

  // Listen for screen lock events
  // useServiceHandler(POWER_MONITOR_KEY.LockScreen, () => {
  //   isLockedRef.current = true
  //   startPolling(LOCKED_INTERVAL)
  // })

  // useServiceHandler(POWER_MONITOR_KEY.UnlockScreen, () => {
  //   isLockedRef.current = false
  //   startPolling(NORMAL_INTERVAL)
  // })

  // useMount(() => {
  //   // Initial data load
  //   getLatestActivity()

  //   // Set up polling
  //   startPolling(NORMAL_INTERVAL)
  // })

  // // Clear polling on component unmount
  // useMount(() => {
  //   return () => {
  //     if (pollIntervalRef.current) {
  //       clearInterval(pollIntervalRef.current)
  //       pollIntervalRef.current = null
  //     }
  //   }
  // })

  return (
    <CardLayout
      seeAllClick={handleNavigateToScreenMonitor}
      title="Latest activity"
      emptyText="No activity in the last 7 days. "
      isEmpty={isEmpty(latestActivity)}>
      {latestActivity ? (
        <ActivityTimelineItem
          activity={{ ...latestActivity, resources: JSON.parse(latestActivity.resources || '[]') } as any}
        />
      ) : null}
    </CardLayout>
  )
}

export { LatestActivityCard }
