// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import React, { useState } from 'react'
import { Typography } from '@arco-design/web-react'
import './home-page.css'
import { Allotment } from 'allotment'
import { useAllotment } from '@renderer/hooks/use-allotment'
import AIToggleButton from '@renderer/components/ai-toggle-button'
import AIAssistant from '@renderer/components/ai-assistant'
import { ProactiveFeedCard } from './components/proactive-feed-card'
import { LatestActivityCard } from './components/latest-activity-card'
import { getRecentVaults } from '@renderer/utils/vault'
import { ToDoCard } from './components/to-do-card'
import { DocColumnsCard } from './components/doc-column-card'
import { ChatCard } from './components/chat-card/chat-card'
import { setActiveConversationId, toggleHomeAiAssistant } from '@renderer/store/chat-history'
import { useSelector } from 'react-redux'
import { RootState, useAppDispatch } from '@renderer/store'
import { useMemoizedFn, useUnmount } from 'ahooks'
import { HeatmapEntry, MonthType } from './components/heatmap/heatmap'

const { Title, Text } = Typography

// const md = new MarkdownIt({
//   html: false,
//   linkify: true,
//   typographer: true
// });

const HomePage: React.FC = () => {
  const recentVaults = getRecentVaults()
  // const { isVisible, toggleAIAssistant, hideAIAssistant } = useAIAssistant()
  const isVisible = useSelector((state: RootState) => state.chatHistory.home.aiAssistantVisible)
  const activeConversationId = useSelector((state: RootState) => state.chatHistory.activeConversationId)
  const { controller, defaultSizes, leftMinSize, rightMinSize } = useAllotment(isVisible)
  const dispatch = useAppDispatch()
  useUnmount(() => {
    dispatch(setActiveConversationId(null))
    dispatch(toggleHomeAiAssistant(false))
  })
  const [selectedDays, setSelectedDays] = useState<string | null>(null)

  const onChange = useMemoizedFn((date: string | null, monthType: MonthType) => {
    if (monthType === MonthType.MONTH && date) {
      setSelectedDays(date)
    }
  })
  return (
    <div className={`flex flex-row h-full allotmentContainer ${!isVisible ? 'allotment-disabled' : ''}`}>
      <Allotment separator={false} ref={controller} defaultSizes={defaultSizes}>
        <Allotment.Pane minSize={leftMinSize}>
          <div style={{ height: '8px', appRegion: 'drag' } as React.CSSProperties} />
          <div className="relative pb-2 h-full w-full overflow-hidden flex flex-col">
            <div className="bg-white rounded-2xl h-full overflow-y-auto overflow-x-hidden pb-2 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
              <div className="flex w-full h-[648px] pt-5 px-4 pb-3 flex-col items-start gap-4 flex-shrink-0">
                <div className="flex justify-between items-start self-stretch w-full">
                  <div className="rounded-xl w-full flex justify-between items-start">
                    <div className="flex w-[639px] flex-col items-start gap-2">
                      <Title heading={3} style={{ marginTop: 5, fontWeight: 700, fontSize: 24 }}>
                        Create with <span style={{ color: 'blue', fontWeight: 700 }}>Context</span>, Clarity from
                        Chaos.👏
                      </Title>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        Home 1s where MineContext proactively delivers your daily summaries, todos, tips and other
                        insights—emerging from all your collected Contexts ✨
                      </Text>
                    </div>
                    <AIToggleButton onClick={() => dispatch(toggleHomeAiAssistant(true))} isActive={isVisible} />
                  </div>
                </div>
                <div className="flex items-start gap-3 flex-1 self-stretch">
                  <div className="flex flex-col items-start gap-3 flex-1 self-stretch">
                    <HeatmapEntry onChange={onChange} />
                    <ToDoCard selectedDays={selectedDays} />
                    <LatestActivityCard
                      title="Latest activity"
                      emptyText="No activity in the last 7 days. "
                      hasToDocButton
                    />
                    <DocColumnsCard vaultsList={recentVaults} />
                    <ChatCard />
                  </div>
                  <ProactiveFeedCard />
                </div>
              </div>
            </div>
          </div>
        </Allotment.Pane>
        <Allotment.Pane minSize={rightMinSize}>
          {isVisible && (
            <AIAssistant
              visible={isVisible}
              onClose={() => dispatch(toggleHomeAiAssistant(false))}
              pageName="home"
              initConversationId={activeConversationId}
            />
          )}
        </Allotment.Pane>
      </Allotment>
    </div>
  )
}

export default HomePage
