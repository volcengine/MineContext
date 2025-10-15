// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useCallback, useMemo } from 'react'
import { debounce } from 'lodash'
import { Card, Spin } from '@arco-design/web-react'
import { useSearchParams } from 'react-router-dom'
import { useVaults } from '@renderer/hooks/useVault'
import MarkdownEditor from '@renderer/components/MarkdownEditor'
import StatusBar from '@renderer/components/StatusBar/StatusBar'
import { Allotment } from 'allotment'
import { useAIAssistant } from '@renderer/hooks/useAIAssistant'
import { useAllotment } from '@renderer/hooks/useAllotment'
import AIToggleButton from '@renderer/components/AIToggleButton'
import AIAssistant from '@renderer/components/AIAssistant'
import { removeMarkdownSymbols } from '@renderer/utils/vault'
import './Vault.css'

const VaultPage = () => {
  const [searchParams] = useSearchParams()
  const id = searchParams.get('id')
  const loading = false
  const error = null

  const { findVaultById, saveVaultContent, saveVaultTitle, updateVault } = useVaults()
  const vault = findVaultById(Number(id))
  const content = vault?.content
  const title = vault?.title ? '## ' + vault.title : ''
  const { isVisible, toggleAIAssistant, hideAIAssistant } = useAIAssistant()
  const { controller, defaultSizes, leftMinSize, rightMinSize } = useAllotment(isVisible)

  const debouncedSave = useMemo(
    () =>
      debounce((value: string, type: 'content' | 'title' | 'summary' | 'tags') => {
        if (type === 'content') {
          saveVaultContent(Number(id), value)
        } else if (type === 'title') {
          saveVaultTitle(Number(id), removeMarkdownSymbols(value))
        } else {
          updateVault(Number(id), { [type]: value })
        }
      }, 300),
    [saveVaultContent, saveVaultTitle, id, updateVault]
  )

  const onMarkdownChange = useCallback(
    (markdown: string, type: 'content' | 'title') => {
      debouncedSave(markdown, type)
    },
    [debouncedSave]
  )

  const onSummaryChange = useCallback(
    (summary: string) => {
      debouncedSave(summary, 'summary')
    },
    [debouncedSave]
  )

  const onTagsChange = useCallback(
    (tags: string) => {
      debouncedSave(tags, 'tags')
    },
    [debouncedSave]
  )

  // Status bar component
  return (
    <div className={`flex flex-row h-full allotmentContainer ${!isVisible ? 'allotment-disabled' : ''}`}>
      <Allotment separator={false} ref={controller} defaultSizes={defaultSizes}>
        <Allotment.Pane minSize={leftMinSize}>
          <div className="vault-page-container">
            <Card className="vault-card">
              {loading || !vault ? (
                <div className="flex justify-center items-center h-full text-[#333]">
                  <Spin tip="Loading..." />
                </div>
              ) : error ? (
                <div className="text-red-500">{error}</div>
              ) : (
                <>
                  <div className="vault-title-container">
                    <MarkdownEditor
                      key={`title-${vault?.id}`}
                      defaultValue={title ?? ''}
                      onChange={(markdown) => onMarkdownChange(markdown, 'title')}
                    />
                  </div>
                  <StatusBar vaultData={vault} onSummaryChange={onSummaryChange} onTagsChange={onTagsChange} />
                  <MarkdownEditor
                    key={vault?.id}
                    defaultValue={content ?? ''}
                    onChange={(markdown) => onMarkdownChange(markdown, 'content')}
                  />
                </>
              )}
            </Card>
            <AIToggleButton onClick={toggleAIAssistant} isActive={isVisible} />
          </div>
        </Allotment.Pane>
        <Allotment.Pane minSize={rightMinSize}>
          <AIAssistant visible={isVisible} onClose={hideAIAssistant} />
        </Allotment.Pane>
      </Allotment>
    </div>
  )
}

export default VaultPage
