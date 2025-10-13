// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { createSlice, PayloadAction } from '@reduxjs/toolkit'

export type NavigationType = 'main' | 'vault'

export interface NavigationState {
  // 当前激活的导航类型
  activeNavigationType: NavigationType
  // 主导航的激活项
  activeMainTab: string
  // 当前激活的 Vault ID（如果在 vault 页面）
  activeVaultId: number | null
}

const initialState: NavigationState = {
  activeNavigationType: 'main',
  activeMainTab: 'home',
  activeVaultId: null,
}

const navigationSlice = createSlice({
  name: 'navigation',
  initialState,
  reducers: {
    setActiveMainTab(state, action: PayloadAction<string>) {
      state.activeNavigationType = 'main'
      state.activeMainTab = action.payload
      state.activeVaultId = null
    },
    setActiveVault(state, action: PayloadAction<number>) {
      state.activeNavigationType = 'vault'
      state.activeVaultId = action.payload
      // 当选择 vault 时，清除主导航的选中状态
      state.activeMainTab = ''
    },
    clearActiveVault(state) {
      state.activeVaultId = null
      // 如果没有主导航选中，默认回到 home
      if (!state.activeMainTab) {
        state.activeNavigationType = 'main'
        state.activeMainTab = 'home'
      }
    },
    // 初始化导航状态，基于当前路由
    initializeFromRoute(state, action: PayloadAction<{ pathname: string; search: string }>) {
      const { pathname, search } = action.payload

      if (pathname === '/vault') {
        // 解析 vault ID
        const urlParams = new URLSearchParams(search)
        const vaultId = urlParams.get('id')
        if (vaultId) {
          state.activeNavigationType = 'vault'
          state.activeVaultId = parseInt(vaultId, 10)
          state.activeMainTab = ''
        }
      } else {
        // 主导航页面
        state.activeNavigationType = 'main'
        state.activeVaultId = null

        // 根据路径设置主导航
        switch (pathname) {
          case '/':
            state.activeMainTab = 'home'
            break
          case '/screen-monitor':
            state.activeMainTab = 'screen-monitor'
            break
          case '/settings': // 添加这一行来处理settings路径
            state.activeMainTab = 'settings'
            break
          default:
            state.activeMainTab = 'home'
        }
      }
    }
  },
})

export const {
  setActiveMainTab,
  setActiveVault,
  clearActiveVault,
  initializeFromRoute
} = navigationSlice.actions

export default navigationSlice.reducer
