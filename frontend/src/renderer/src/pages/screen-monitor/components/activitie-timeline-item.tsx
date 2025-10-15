// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { FC } from 'react'
import { Activity } from '../ScreenMonitor'
import { Popover, Image } from '@arco-design/web-react'
export interface ActivityTimelineItemProps {
  activity: Activity
}
const ActivityTimelineItem: FC<ActivityTimelineItemProps> = (props) => {
  const { activity } = props

  return (
    <div className="pb-[24px] text-[14px]">
      <Popover
        content={activity.content}
        trigger="hover"
        triggerProps={{ position: 'tl' }}
        disabled={!activity.content}>
        <div className="cursor-pointer font-bold text-[12px] text-black pb-[12px] hover:font-extrabold">
          {activity.title}
        </div>
      </Popover>
      <div className="screenshots-container flex flex-wrap align-center gap-2">
        <Image.PreviewGroup infinite className="[&_.arco-image-preview-img]:!scale-80">
          {(activity?.resources || [])
            .filter((resource) => resource.type === 'image')
            .map((resource, index) => {
              return (
                <Image
                  key={index}
                  src={`file://${encodeURI(resource.path)}`}
                  width={110}
                  height={60}
                  alt={`lamp${index + 1}`}
                  className="cursor-pointer rounded-[8px] overflow-hidden"
                />
              )
            })}
        </Image.PreviewGroup>
      </div>
    </div>
  )
}
export { ActivityTimelineItem }
