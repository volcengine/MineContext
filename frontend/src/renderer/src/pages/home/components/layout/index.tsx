// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { Card } from '@arco-design/web-react'
import { FC } from 'react'

interface LatestActivityCardProps {
  title: string
  emptyText?: string
  children?: React.ReactNode
  seeAllClick?: () => void
  isEmpty?: boolean
}

const CardLayout: FC<LatestActivityCardProps> = (props) => {
  const { title, seeAllClick, emptyText, children, isEmpty } = props

  return (
    <Card
      headerStyle={{ width: '100%' }}
      bodyStyle={{ width: '100%', overflowY: 'auto', scrollbarWidth: 'none', flex: '1' }}
      title={
        <div className="flex items-center gap-2 self-stretch">
          <div className="flex-1 text-black font-['Roboto'] text-sm font-medium leading-[22px]">{title}</div>
          {seeAllClick ? (
            <div
              className="text-[var(--text-color-text-2,#3F3F51)] font-['PingFang SC'] text-xs leading-[20px] cursor-pointer font-medium"
              onClick={seeAllClick}>
              See all
            </div>
          ) : null}
        </div>
      }
      className="flex w-full h-[160px] p-3 flex-col items-start gap-3 self-stretch rounded-[10px] border border-[rgba(225,227,239,0.80)] bg-white">
      <div
        className={`flex flex-col items-center gap-1 flex-1 self-stretch ${isEmpty ? '' : 'justify-start items-start'} h-full`}>
        {!isEmpty ? (
          children
        ) : (
          <div className="flex w-[340px] h-full flex-col justify-center items-center text-[var(--text-color-text-3,#6E718C)] text-center font-['Roboto'] text-[13px] font-normal leading-[22px] tracking-[0.039px]">
            {emptyText}
          </div>
        )}
      </div>
    </Card>
  )
}

export { CardLayout }
