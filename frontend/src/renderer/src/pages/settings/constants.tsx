// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { once } from 'lodash'
import { ReactNode } from 'react'
import openAI from '../../assets/images/settings/OpenAI.png'
import doubao from '../../assets/images/settings/doubao.png'
import custom from '../../assets/images/settings/custom.svg'

export enum ModelTypeList {
  Doubao = 'doubao',
  OpenAI = 'openai',
  Custom = 'custom'
}

export enum embeddingModels {
  DoubaoEmbeddingModelId = 'doubao-embedding-large-text-240915',
  OpenAIEmbeddingModelId = 'text-embedding-3-large'
}
export enum BaseUrl {
  DoubaoUrl = 'https://ark.cn-beijing.volces.com/api/v3',
  OpenAIUrl = 'https://api.openai.com/v1'
}
export interface OptionInfo {
  value: string
  label: string
}
export interface ModelInfo {
  icon: ReactNode
  key: string
  value: string
  option?: OptionInfo[]
}

export const ModelInfoMap = once((): ModelInfo[] => [
  {
    icon: <img src={doubao} className="!max-w-none w-[24px] h-[24px]" />,
    key: 'Doubao',
    value: 'doubao',
    option: [
      {
        value: 'doubao-seed-1-6-flash-250828',
        label: 'doubao-seed-1.6-flash'
      },
      {
        value: 'doubao-1-5-vision-pro-250328',
        label: 'doubao-1.5-vision-pro'
      },
      {
        value: 'doubao-1-5-vision-lite-250315',
        label: 'doubao-1.5-vision-lite'
      }
    ]
  },
  {
    icon: <img src={openAI} className="!max-w-none w-[24px] h-[24px]" />,
    key: 'OpenAI',
    value: 'openai',
    option: [
      {
        value: 'gpt-4.1',
        label: 'GPT-4.1'
      },
      {
        value: 'gpt-4.1-mini',
        label: 'GPT-4.1 Mini'
      },
      {
        value: 'gpt-4.1-nano',
        label: 'GPT-4.1 Nano'
      }
    ]
  },
  {
    icon: <img src={custom} className="!max-w-none w-[18px] h-[18px]" />,
    key: 'Custom',
    value: 'custom'
  }
])
