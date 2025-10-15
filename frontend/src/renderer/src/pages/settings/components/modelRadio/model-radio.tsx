// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { ModelInfoMap } from '../../constants'
interface ModelRadioProps {
  value?: string
  onChange?: (v: string) => void
}

const ModelRadio = ({ value, onChange }: ModelRadioProps) => {
  const ModelInfoList = ModelInfoMap()
  return (
    <div className="w-[100px] flex items-center justify-between gap-[16px]">
      {ModelInfoList?.map((item) => {
        return (
          <div className="w-10  cursor-pointer">
            <div
              className={`w-10 h-10 rounded-full border flex items-center justify-center overflow-hidden ${item.value === value ? 'border-[#5252FF]' : 'border-gray-300'} ${item.value === value ? 'border-2' : 'border-1'}`}
              onClick={() => {
                onChange?.(item.value)
              }}>
              <div>
                <div className="w-full h-full flex items-center justify-center">{item.icon}</div>
              </div>
            </div>
            <div className="w-10 h-3 mt-[4px] flex items-center justify-center overflow-hidden text-[#6E718C] text-[10px]">
              {item.key}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default ModelRadio
