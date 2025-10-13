// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

/// <reference types="vite/client" />
/// <reference types="./types/electron.d.ts" />

import { NavigateFunction } from 'react-router-dom'

interface ImportMetaEnv {
  VITE_RENDERER_INTEGRATED_MODEL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare global {
  interface Window {
    root: HTMLElement
    store: any
    navigate: NavigateFunction
  }
}
