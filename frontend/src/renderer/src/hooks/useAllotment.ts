// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useRef, useMemo } from 'react';
import { AllotmentHandle } from 'allotment';

const LeftMinSize = 600;
const RightVisibleMinSize = 340;
const RightHiddenMinSize = 0;

export const useAllotment = (isVisible: boolean) => {
  const controller = useRef<AllotmentHandle>(null);

  // 计算默认大小
  const defaultSizes = useMemo(() => {
    return isVisible ? [600, 340] : [1000, 0];
  }, [isVisible]);

  // 当 AI 助手显示/隐藏时，调整 Allotment 的大小
  useEffect(() => {
    if (controller.current) {
      if (isVisible) {
        // 显示 AI 助手时，设置合适的大小比例，确保第二个面板至少 340px
        const containerWidth = window.innerWidth;
        const leftPanelWidth = Math.max(LeftMinSize, containerWidth - RightVisibleMinSize);
        controller.current.resize([leftPanelWidth, RightVisibleMinSize]);
      } else {
        // 隐藏 AI 助手时，让第一个面板占满全宽
        controller.current.resize([1000, 0]);
      }
    }
  }, [isVisible]);

  const rightMinSize = useMemo(() => {
    return isVisible ? RightVisibleMinSize : RightHiddenMinSize;
  }, [isVisible]);

  return {
    controller,
    defaultSizes,
    rightMinSize,
    leftMinSize: LeftMinSize,
  };
};
