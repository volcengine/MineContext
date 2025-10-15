// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { PushDataTypes } from '@renderer/constant/feed'
import React, { FC, useMemo, useState } from 'react'
import { Message } from '@arco-design/web-react'
import { IconClose } from '@arco-design/web-react/icon'
import dayjs from 'dayjs'
import removeMarkdown from 'remove-markdown'
import { FeedEvent, useEvents } from '@renderer/hooks/useEvents'
import { ProactiveFeedModal } from '@renderer/components/ProactiveFeedModal'
import { formatRelativeTime } from '@renderer/utils/time'
import chatIcon from '@renderer/assets/icons/chat-icon.svg'
import feedEmptyIcon from '@renderer/assets/icons/feed-empty.svg'

// Define the properties received by the component
interface FeedCardProps {
  id: string
  feedType: PushDataTypes // Card type (used to control styles, icons)
  time: string
  desc?: string
  doc_id?: string // Optional: document ID, for navigation
  doc_title?: string // Optional: document title, for display
  doc_content?: string // Optional: document content, for display
}

const ProactiveFeedCardItem: FC<FeedCardProps> = (props) => {
  const { id, feedType, time, desc, doc_content } = props
  // const isDocument =
  //   feedType === PushDataTypes.DAILY_SUMMARY_GENERATED || feedType === PushDataTypes.WEEKLY_SUMMARY_GENERATED
  // const { navigateToVault } = useNavigation()
  const [visible, setVisible] = useState(false)
  const { removeEvent, setCurrentActiveEvent } = useEvents()
  // const handleNavigateToVault = () => {
  //   if (doc_id) {
  //     navigateToVault(Number(doc_id))
  //   }
  // }

  const handleChat = () => {
    setCurrentActiveEvent(id)
    setVisible(true)
  }

  const [eventIcon, eventTitle] = useMemo(() => {
    switch (feedType) {
      case PushDataTypes.TIP_GENERATED:
        return ['💡', 'Tip']
      case PushDataTypes.DAILY_SUMMARY_GENERATED:
        return ['👋', 'Daily Summary']
      case PushDataTypes.WEEKLY_SUMMARY_GENERATED:
        return ['🌟', 'Weekly Summary']
      default:
        return ['🔔', 'New Notification']
    }
  }, [feedType])

  const handleRemoveEvent = (id: string) => {
    removeEvent(id)
    Message.success('insight deleted')
  }

  return (
    <div className="flex flex-col items-start  py-2 pr-3 pl-2 gap-2 w-full rounded-lg bg-[var(--background-color-bg-2,#FAFBFD)] group">
      <div className="flex items-start gap-2  w-full">
        <div>{eventIcon}</div>
        <div className="flex flex-col items-start gap-1 w-full">
          <div className="flex justify-between items-center w-full">
            <div className="flex gap-2 items-center flex-1">
              <div className="text-black font-['Roboto'] text-[13px] leading-[22px] font-medium">{eventTitle}</div>
            </div>
            <div className="text-[var(--text-color-text-3,#6E718C)] font-['Roboto'] text-xs font-normal leading-5 group-hover:hidden">
              {formatRelativeTime(time)}
            </div>
            <div
              className="cursor-pointer text-[14px] text-[#939393] hidden group-hover:block"
              onClick={() => handleRemoveEvent(id)}>
              <IconClose />
            </div>
          </div>
          <div className="text-[var(--text-color-text-1,#0B0B0F)] w-full font-[Roboto] text-[13px] font-normal leading-[18px]">
            {removeMarkdown(desc || '')}
          </div>
          <div className="flex items-center gap-3">
            {/* {isDocument && (
              <div
                className="text-[#5252FF] font-['PingFang SC'] text-[13px] leading-[22px] tracking-[0.039px] font-medium cursor-pointer"
                style={{
                  fontWeight: 500
                }}
                onClick={handleNavigateToVault}>
                View
              </div>
            )} */}
            <div className="flex items-center gap-1 cursor-pointer" onClick={handleChat}>
              <div>
                <img src={chatIcon} alt="chat icon" />
              </div>
              <div className="text-[var(--text-color-text-3,#5252FF)] font-['Roboto'] text-xs font-normal leading-5">
                Check
              </div>
            </div>
          </div>
        </div>
      </div>
      <ProactiveFeedModal
        visible={visible}
        onCancel={() => setVisible(false)}
        content={doc_content || ''}
        time={formatRelativeTime(time)}
      />
    </div>
  )
}

const ProactiveFeedCard: React.FC = ({}) => {
  const { feedEvents } = useEvents()
  const transferType = (event: FeedEvent): FeedCardProps => {
    return {
      id: event.id,
      feedType: event.type,
      time: dayjs(event.timestamp).format('YYYY-MM-DD HH:mm:ss'),
      desc: event.data.title as string,
      doc_id: event.data.doc_id as string,
      doc_title: event.data.title as string,
      doc_content: event.data.content as string
    }
  }
  const sortedEventsList = [...feedEvents].reverse()
  const isEmpty = sortedEventsList.length === 0
  return (
    <div className="flex w-[256px] flex-col items-start gap-4 self-stretch rounded-[12px] bg-white h-[700px]">
      <div className="flex items-center gap-2 w-full">
        <div className="flex px-[2px] justify-center items-center gap-[4px] rounded-[2px] bg-gradient-to-l from-[rgba(239,251,248,0.5)] to-[#F5FBEF]">
          💡
          <div className="font-['Byte Sans'] text-[15px] font-extralight leading-[22px] tracking-[0.045px] bg-gradient-to-l from-[#00C469] to-[#0026B1] bg-clip-text text-transparent">
            Proactive
          </div>
        </div>
        <div
          className="text-black font-['Roboto'] text-sm font-medium leading-[22px] tracking-[0.042px]"
          style={{
            fontWeight: 500
          }}>
          Feed
        </div>
      </div>
      <div
        className={`flex flex-col item-center ${!isEmpty && 'items-start'} gap-[6px] flex-1 self-stretch h-[500px] overflow-y-auto`}>
        {!isEmpty ? (
          sortedEventsList.map((event) => <ProactiveFeedCardItem key={event.id} {...transferType(event)} />)
        ) : (
          <div className="flex flex-col items-center justify-center mt-14 gap-[8px]">
            <img src={feedEmptyIcon} alt="empty icon" />
            <div className="w-[182px] text-center text-[#6E718C] font-roboto text-[12px] font-normal leading-[20px] tracking-[0.036px]">
              Proactive insights will appear here to help you
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export { ProactiveFeedCard }
