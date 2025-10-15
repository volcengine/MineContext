// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useCallback } from 'react'
import { useSelector } from 'react-redux'
import { RootState, useAppDispatch } from '@renderer/store'
import { setScreenSettings as setScreenSettingsAction } from '@renderer/store/setting'

export const useSetting = () => {
  const dispatch = useAppDispatch()
  const screenSettings = useSelector((state: RootState) => state.setting.screenSettings)

  const { recordInterval, recordingHours, enableRecordingHours, applyToDays } = screenSettings

  const setRecordInterval = useCallback(
    (interval: number) => {
      dispatch(setScreenSettingsAction({ recordInterval: interval }))
    },
    [dispatch]
  )

  const setEnableRecordingHours = useCallback(
    (enable: boolean) => {
      dispatch(setScreenSettingsAction({ enableRecordingHours: enable }))
    },
    [dispatch]
  )

  const setRecordingHours = useCallback(
    (hours: [string, string]) => {
      dispatch(setScreenSettingsAction({ recordingHours: hours }))
    },
    [dispatch]
  )

  const setApplyToDays = useCallback(
    (days: 'weekday' | 'everyday') => {
      dispatch(setScreenSettingsAction({ applyToDays: days }))
    },
    [dispatch]
  )

  return {
    recordInterval,
    recordingHours,
    enableRecordingHours,
    applyToDays,
    setRecordInterval,
    setEnableRecordingHours,
    setRecordingHours,
    setApplyToDays
  }
}
