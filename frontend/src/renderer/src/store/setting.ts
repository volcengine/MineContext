// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { createSlice, PayloadAction } from '@reduxjs/toolkit'

export const defaultScreenSettings = {
  recordInterval: 15,
  enableRecordingHours: false,
  recordingHours: ['08:00:00', '20:00:00'] as [string, string],
  applyToDays: 'weekday'
};

export type ScreenSettings = typeof defaultScreenSettings;

const initialState = {
  screenSettings: defaultScreenSettings
  // other settings...
}

const settingSlice = createSlice({
  name: 'settings',
  initialState,
  reducers: {
    setScreenSettings(state, action: PayloadAction<Partial<ScreenSettings>>) {
      state.screenSettings = { ...state.screenSettings, ...action.payload }
    }
  }
})

export const { setScreenSettings } = settingSlice.actions

export default settingSlice.reducer
