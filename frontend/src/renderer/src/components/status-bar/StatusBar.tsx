// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Input, Tag } from '@arco-design/web-react'
import { Vault } from '@renderer/types'
import dayjs from 'dayjs'

interface StatusBarProps {
  vaultData: Vault | null
  onSummaryChange: (summary: string) => void
  onTagsChange: (tags: string) => void
}

const StatusBar: React.FC<StatusBarProps> = ({ vaultData, onSummaryChange, onTagsChange }) => {
  const { t } = useTranslation()
  const [isEditingSummary, setIsEditingSummary] = useState(false)
  const [isEditingTags, setIsEditingTags] = useState(false)

  if (!vaultData) {
    return null
  }

  const renderRow = (label: string, value: React.ReactNode, className?: string): React.ReactElement => (
    <div className={`flex items-center !mb-[12px] !text-[14px] ${className || ''}`}>
      <span className="text-[#666] w-[140px]">{label} :</span>
      <div className="text-[#333] w-full">{value}</div>
    </div>
  )

  const tags =
    typeof vaultData.tags === 'string' && vaultData.tags.trim() ? vaultData.tags.split(',').map((t) => t.trim()) : []

  return (
    <div className="status-bar-container">
      {renderRow(
        t('status_bar.created_at', 'Created at'),
        vaultData.created_at ? dayjs(vaultData.created_at).format('MMMM D, YYYY HH:mm:ss') : 'N/A'
      )}
      {renderRow(t('status_bar.capture_method', 'Capture method'), t('status_bar.creation', 'Creation'))}
      {renderRow(t('status_bar.process_method', 'Process method'), t('status_bar.smart_summary', 'Smart Summary'))}
      {renderRow(t('status_bar.context_type', 'Context type'), t('status_bar.knowledge_context', 'Knowledge Context'))}
      {renderRow(
        t('status_bar.summary', 'Summary'),
        isEditingSummary ? (
          <Input.TextArea
            defaultValue={vaultData.summary || ''}
            onChange={onSummaryChange}
            onBlur={() => setIsEditingSummary(false)}
            placeholder={t('status_bar.enter_summary', 'Enter summary')}
            autoSize
            autoFocus
            className="w-full"
          />
        ) : (
          <div
            onClick={() => {
              setIsEditingSummary(true)
            }}
            className="min-h-[22px] cursor-text w-full">
            {vaultData.summary || <span className="text-[#aaa]">{t('status_bar.no_summary', 'No summary')}</span>}
          </div>
        )
      )}
      {renderRow(
        t('status_bar.tags', 'Tags'),
        <div className="flex flex-wrap items-center min-h-[32px] gap-x-[4px] gap-y-[4px]">
          {tags.length > 0 ? (
            tags.map((tag, index) => (
              <Tag key={index} className="mr-[8px] mb-[4px]">
                {tag}
              </Tag>
            ))
          ) : (
            <div className="text-[#aaa] mr-[8px]">{t('status_bar.no_tags', 'No tags')}</div>
          )}
          {isEditingTags ? (
            <Input
              defaultValue=""
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const value = e.currentTarget.value.trim()
                  if (value.includes(',')) {
                    return
                  }
                  if (value) {
                    const newTags = [...tags, value]
                    onTagsChange(newTags.join(', '))
                    setIsEditingTags(false)
                  }
                }
              }}
              onBlur={() => setIsEditingTags(false)}
              placeholder={t('status_bar.enter_new_tag', 'Enter new tag')}
              autoFocus
              className="!w-[120px] mr-[8px] mb-[4px] !inline-block"
            />
          ) : (
            <Tag
              className="mb-[4px] cursor-pointer bg-[#f0f0f0] !border-[#d9d9d9] !border-dashed border"
              onClick={(e) => {
                e.stopPropagation()
                setIsEditingTags(true)
              }}>
              {t('status_bar.new_tag', '+ New tag')}
            </Tag>
          )}
        </div>,
        'items-start'
      )}
    </div>
  )
}

export default StatusBar
