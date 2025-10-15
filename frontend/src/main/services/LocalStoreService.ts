// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import Store from 'electron-store'
import { get } from 'lodash'
const LocalStore = get(Store, 'default', Store)
class LocalStoreService {
  private store: Store

  constructor() {
    this.store = new LocalStore()
  }

  public getSetting(key: string) {
    return this.store.get(key)
  }

  public setSetting(key: string, value: any) {
    this.store.set(key, value)
  }
  public clearSetting(key: string) {
    this.store.delete(key)
  }
}
const localStoreService = new LocalStoreService()
export { localStoreService }
