// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'

dayjs.extend(utc)
dayjs.extend(timezone)

// Store to SQLite (always store in UTC)
export const toSqliteDatetime = (date: Date | string | number): string => {
  return dayjs(date).utc().format('YYYY-MM-DD HH:mm:ss')
}
export const isValidIsoString = (isoString: string): boolean => {
  // 第二个参数 true 表示启用严格模式，要求格式和 ISO 8601 完全匹配
  return dayjs(isoString).isValid()
}
// Read from SQLite (convert to local time zone)
export const fromSqliteDatetime = (sqliteDate: string, tz: string = dayjs.tz.guess()): string => {
  return dayjs.utc(sqliteDate).tz(tz).format('YYYY-MM-DD HH:mm:ss')
}
