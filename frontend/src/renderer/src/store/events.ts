// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { PushDataTypes } from '@renderer/constant/feed'

export interface EventType {
  id: string
  type: PushDataTypes
  data: Record<string, any>
  timestamp: number
}

const initialState = {
  events: [] as EventType[],
  activeEvent: null as EventType | null,
  isModalVisible: false
}

const eventsSlice = createSlice({
  name: 'events',
  initialState,
  reducers: {
    addEvent(state, action: PayloadAction<EventType[]>) {
      if (action.payload) {
        const newEvents = action.payload.map((e) => ({
          ...e,
          timestamp: Math.floor(e.timestamp * 1000) // Handle timestamp digits
        }))
        state.events.push(...newEvents)
      }
    },
    removeExistEvent(state, action: PayloadAction<string>) {
      state.events = state.events.filter((event) => event.id !== action.payload)
    },
    setActiveEvent(state, action: PayloadAction<string>) {
      state.activeEvent = state.events.find((event) => event.id === action.payload) || null
    },
    setIsModalVisible(state, action: PayloadAction<boolean>) {
      state.isModalVisible = action.payload
    }
  }
})

export const { addEvent, removeExistEvent, setActiveEvent, setIsModalVisible } = eventsSlice.actions

export default eventsSlice.reducer
