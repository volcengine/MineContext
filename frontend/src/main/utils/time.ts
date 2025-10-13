// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'

dayjs.extend(utc)
dayjs.extend(timezone)

// 存储到 SQLite (始终存 UTC)
export const toSqliteDatetime = (date: Date | string | number): string => {
  return dayjs(date).utc().format('YYYY-MM-DD HH:mm:ss')
}

// 从 SQLite 读取 (转成本地时区)
export const fromSqliteDatetime = (sqliteDate: string, tz: string = dayjs.tz.guess()): string => {
  return dayjs.utc(sqliteDate).tz(tz).format('YYYY-MM-DD HH:mm:ss')
}
