// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useNavigation } from '@renderer/hooks/useNavigation'
import { FC, useRef } from 'react'
import { CardLayout } from '../layout'
import { useMount, useRequest } from 'ahooks'
import { ActivityTimelineItem } from '@renderer/pages/screen-monitor/components/activitie-timeline-item'
import { isEmpty } from 'lodash'

interface LatestActivityCardProps {
  title: string
  hasToDocButton?: boolean
  emptyText?: string
  children?: React.ReactNode
}

const LatestActivityCard: FC<LatestActivityCardProps> = () => {
  const { navigateToMainTab } = useNavigation()

  // 存储轮询定时器ID
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const handleNavigateToScreenMonitor = () => {
    navigateToMainTab('screen-monitor', '/screen-monitor')
  }

  const { run: getLatestActivity, data } = useRequest<Activity, any>(async () => {
    const res = await window.dbAPI.getLatestActivity()
    return res as Activity
  })

  useMount(() => {
    // 初始加载数据
    getLatestActivity()

    // 设置轮询，每60秒更新一次数据
    pollIntervalRef.current = setInterval(() => {
      getLatestActivity()
    }, 60000) // 60000毫秒 = 60秒
  })

  // 在组件卸载时清除轮询
  useMount(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
    }
  })

  return (
    <CardLayout
      seeAllClick={handleNavigateToScreenMonitor}
      title="Latest activity"
      emptyText="No activity in the last 7 days. "
      isEmpty={isEmpty(data)}>
      {data ? (
        <ActivityTimelineItem
          activity={{ ...data, resources: JSON.parse(data.resources || JSON.stringify('{}')) } as any}
        />
      ) : null}
    </CardLayout>
  )
}

export { LatestActivityCard }
