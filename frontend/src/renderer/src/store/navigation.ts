// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { createSlice, PayloadAction } from '@reduxjs/toolkit'

export type NavigationType = 'main' | 'vault'

export interface NavigationState {
  // Currently active navigation type
  activeNavigationType: NavigationType
  // Active item in the main navigation
  activeMainTab: string
  // Currently active Vault ID (if on the vault page)
  activeVaultId: number | null
}

const initialState: NavigationState = {
  activeNavigationType: 'main',
  activeMainTab: 'home',
  activeVaultId: null
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
      // When a vault is selected, clear the selection state of the main navigation
      state.activeMainTab = ''
    },
    clearActiveVault(state) {
      state.activeVaultId = null
      // If no main navigation is selected, default back to home
      if (!state.activeMainTab) {
        state.activeNavigationType = 'main'
        state.activeMainTab = 'home'
      }
    },
    // Initialize navigation state based on the current route
    initializeFromRoute(state, action: PayloadAction<{ pathname: string; search: string }>) {
      const { pathname, search } = action.payload

      if (pathname === '/vault') {
        // Parse vault ID
        const urlParams = new URLSearchParams(search)
        const vaultId = urlParams.get('id')
        if (vaultId) {
          state.activeNavigationType = 'vault'
          state.activeVaultId = parseInt(vaultId, 10)
          state.activeMainTab = ''
        }
      } else {
        // Main navigation page
        state.activeNavigationType = 'main'
        state.activeVaultId = null

        // Set main navigation based on the path
        switch (pathname) {
          case '/':
            state.activeMainTab = 'home'
            break
          case '/screen-monitor':
            state.activeMainTab = 'screen-monitor'
            break
          case '/settings': // Add this line to handle the settings path
            state.activeMainTab = 'settings'
            break
          default:
            state.activeMainTab = 'home'
        }
      }
    }
  }
})

export const { setActiveMainTab, setActiveVault, clearActiveVault, initializeFromRoute } = navigationSlice.actions

export default navigationSlice.reducer
