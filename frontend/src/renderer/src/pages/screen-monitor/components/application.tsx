// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { FC } from 'react'
import { Button } from '@arco-design/web-react'
import screenIcon from '@renderer/assets/icons/screen.svg'
import clsx from 'clsx'
export interface ApplicationProps {
  value?: any[]
  onCancel?: () => void
  visible?: boolean
  onOk?: () => void
}

const Application: FC<ApplicationProps> = (props) => {
  const { value: source = [], onCancel, visible, onOk } = props
  return (
    <div className="flex justify-between items-center">
      {source.length > 0 ? (
        <div className="flex items-center flex-1">
          <div className="flex items-center relative flex-1 h-[32px]">
            {source.slice(0, 9).map((item, index) => {
              return (
                <div
                  key={item.id}
                  className={clsx(
                    'w-[32px] h-[32px] rounded-[32px] flex items-center justify-center bg-white border border-solid border-[#efeff4]',
                    'absolute top-0',
                    index === 0 ? `left-0` : ``
                  )}
                  style={{ left: `${index * 20}px` }}>
                  <div className="w-[28px] h-[28px] rounded-[28px] flex items-center justify-center bg-[#ededf2]">
                    {item.type === 'window' ? (
                      <img
                        src={item.appIcon || item.thumbnail || ''}
                        alt={item.name || ''}
                        className="w-[18px] h-[18px]"
                      />
                    ) : null}
                    {item.type === 'screen' ? <img src={screenIcon} alt="" className="w-[16px] h-[16px]" /> : null}
                  </div>
                </div>
              )
            })}
          </div>
          {source.length > 9 ? (
            <div className="text-[12px] leading-[16px] text-[#42464e]">+{source.length - 9}</div>
          ) : null}
        </div>
      ) : null}
      {!visible ? (
        <Button type="text" className="!px-0 ml-[24px]" onClick={onOk}>
          Select
        </Button>
      ) : (
        <Button type="text" className="!px-0 ml-[24px]" onClick={onCancel}>
          Close
        </Button>
      )}
    </div>
  )
}
export { Application }
