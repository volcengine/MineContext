// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { loggerService } from '@logger'
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

const logger = loggerService.withContext('Store')

const rootReducer = combineReducers({
  navigation,
  setting,
  screen,
  vault,
  events
})

// 桌面应用持久化配置，主要为了下次打开数据还能恢复
const persistedReducer = persistReducer(
  {
    key: 'vikingdb',
    storage,
    version: 1,
    blacklist: ['vault', 'screen'] // 不持久化vault，vault数据存在sqlite数据表中
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
