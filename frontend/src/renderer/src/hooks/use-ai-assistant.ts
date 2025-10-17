// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useState, useEffect, useCallback } from 'react';

export const useAIAssistant = () => {
  const [isVisible, setIsVisible] = useState(false)

  const toggleAIAssistant = useCallback(() => {
    setIsVisible((prev) => !prev)
  }, [])

  const showAIAssistant = useCallback(() => {
    setIsVisible(true)
  }, [])

  const hideAIAssistant = useCallback(() => {
    setIsVisible(false)
  }, [])

  // Handle shortcut Command+P (Mac)
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'p') {
        event.preventDefault()
        toggleAIAssistant()
      }

      // Close AI assistant with ESC key
      if (event.key === 'Escape' && isVisible) {
        hideAIAssistant()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [toggleAIAssistant, hideAIAssistant, isVisible])

  return {
    isVisible,
    toggleAIAssistant,
    showAIAssistant,
    hideAIAssistant
  }
}
