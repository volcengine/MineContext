// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useRef, useMemo } from 'react'
import { AllotmentHandle } from 'allotment'

const LeftMinSize = 600
const RightVisibleMinSize = 340
const RightHiddenMinSize = 0

export const useAllotment = (isVisible: boolean) => {
  const controller = useRef<AllotmentHandle>(null)

  // Calculate default sizes
  const defaultSizes = useMemo(() => {
    return isVisible ? [600, 340] : [1000, 0]
  }, [isVisible])

  // Adjust Allotment size when AI assistant is shown/hidden
  useEffect(() => {
    if (controller.current) {
      if (isVisible) {
        // When showing the AI assistant, set an appropriate size ratio to ensure the second panel is at least 340px
        const containerWidth = window.innerWidth
        const leftPanelWidth = Math.max(LeftMinSize, containerWidth - RightVisibleMinSize)
        controller.current.resize([leftPanelWidth, RightVisibleMinSize])
      } else {
        // When hiding the AI assistant, make the first panel take up the full width
        controller.current.resize([1000, 0])
      }
    }
  }, [isVisible])

  const rightMinSize = useMemo(() => {
    return isVisible ? RightVisibleMinSize : RightHiddenMinSize
  }, [isVisible])

  return {
    controller,
    defaultSizes,
    rightMinSize,
    leftMinSize: LeftMinSize
  }
}
