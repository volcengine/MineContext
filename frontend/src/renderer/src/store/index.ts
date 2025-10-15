// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { combineReducers, configureStore } from '@reduxjs/toolkit'
import { useDispatch, useSelector, useStore } from 'react-redux'
import { FLUSH, PAUSE, PERSIST, persistReducer, persistStore, PURGE, REGISTER, REHYDRATE } from 'redux-persist'
import storage from 'redux-persist/lib/storage'

import storeSyncService from '../services/StoreSyncService'
import navigation from './navigation'
import screen from './screen'
import setting from './setting'
import vault from './vault'
import events from './events'

import { getLogger } from '@shared/logger/renderer'

const logger = getLogger('Store')

const rootReducer = combineReducers({
  navigation,
  setting,
  screen,
  vault,
  events
})

// Desktop application persistence configuration, mainly for data recovery on next launch
const persistedReducer = persistReducer(
  {
    key: 'vikingdb',
    storage,
    version: 1,
    blacklist: ['vault', 'screen'] // Do not persist vault, vault data is stored in the sqlite data table
  },
  rootReducer
)

const store = configureStore({
  // @ts-ignore store type is unknown
  reducer: persistedReducer as typeof rootReducer,
  middleware: (getDefaultMiddleware) => {
    return getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER]
      }
    }).concat(storeSyncService.createMiddleware())
  },
  devTools: true
})
storeSyncService.init(store, {
  syncList: ['screen/', 'setting/']
})

export type RootState = ReturnType<typeof rootReducer>
export type AppDispatch = typeof store.dispatch

export const persistor = persistStore(store)
export const useAppDispatch = useDispatch.withTypes<AppDispatch>()
export const useAppSelector = useSelector.withTypes<RootState>()
export const useAppStore = useStore.withTypes<typeof store>()
window.store = store

export async function handleSaveData() {
  logger.info('Flushing redux persistor data')
  await persistor.flush()
  logger.info('Flushed redux persistor data')
}

export default store
