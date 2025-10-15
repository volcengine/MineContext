// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import React from 'react'
import { Typography } from '@arco-design/web-react'
import './HomePage.css'
import { Allotment } from 'allotment'
import { useAIAssistant } from '@renderer/hooks/useAIAssistant'
import { useAllotment } from '@renderer/hooks/useAllotment'
import AIToggleButton from '@renderer/components/AIToggleButton'
import AIAssistant from '@renderer/components/AIAssistant'
import { ProactiveFeedCard } from './components/ProactiveFeedCard'
import { LatestActivityCard } from './components/latest-activity-card'
import { getRecentVaults } from '@renderer/utils/vault'
import { ToDoCard } from './components/to-do-card'
import { DocColumnsCard } from './components/doc-column-card'

const { Title, Text } = Typography

// const md = new MarkdownIt({
//   html: false,
//   linkify: true,
//   typographer: true
// });

const HomePage: React.FC = () => {
  const recentVaults = getRecentVaults()
  const { isVisible, toggleAIAssistant, hideAIAssistant } = useAIAssistant()
  const { controller, defaultSizes, leftMinSize, rightMinSize } = useAllotment(isVisible)

  return (
    <div className={`flex flex-row h-full allotmentContainer ${!isVisible ? 'allotment-disabled' : ''}`}>
      <Allotment separator={false} ref={controller} defaultSizes={defaultSizes}>
        <Allotment.Pane minSize={leftMinSize}>
          <div className="homepage-container">
            <div className="homepage-container-inner">
              <div className="flex w-full h-[648px] pt-5 px-4 pb-3 flex-col items-start gap-4 flex-shrink-0">
                <div className="flex justify-between items-start self-stretch w-full">
                  <div className="rounded-xl w-full flex justify-between items-start">
                    <div className="flex w-[639px] flex-col items-start gap-2">
                      <Title heading={3} style={{ marginTop: 5, fontWeight: 700, fontSize: 24 }}>
                        Create with <span style={{ color: 'blue', fontWeight: 700 }}>Context</span>, Clarity from
                        Chaos.👏
                      </Title>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        Home is where MineContext proactively delivers your daily summaries, todos, tips and other
                        insights—emerging from all your collected Contexts ✨
                      </Text>
                    </div>
                    <AIToggleButton onClick={toggleAIAssistant} isActive={isVisible} />
                  </div>
                </div>
                <div className="flex items-start gap-3 flex-1 self-stretch">
                  <div className="flex flex-col items-start gap-3 flex-1 self-stretch">
                    <ToDoCard />
                    <LatestActivityCard
                      title="Latest activity"
                      emptyText="No activity in the last 7 days. "
                      hasToDocButton
                    />
                    <DocColumnsCard vaultsList={recentVaults} />
                  </div>
                  <ProactiveFeedCard />
                </div>
              </div>
            </div>
          </div>
          {/* <ProactiveFeedModal
            isVisible={currentModalVisible}
            handleConfirm={() => {
              setCurrentModalVisible(false)
            }}
            event={activeEvent!}
          /> */}
        </Allotment.Pane>
        <Allotment.Pane minSize={rightMinSize}>
          {isVisible && <AIAssistant visible={isVisible} onClose={hideAIAssistant} />}
        </Allotment.Pane>
      </Allotment>
    </div>
  )
}

export default HomePage
