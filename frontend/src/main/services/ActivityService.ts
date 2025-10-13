// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { DB } from './Database' // 确保引入 DB 类

class ActivityService {
  /**
   * 获取数据库中最新的一条 Activity 记录。
   * "最新" 是根据 start_time 降序排列确定的。
   * @returns {Activity | undefined} 返回最新的 Activity 对象，如果表中没有数据则返回 undefined。
   */
  public getLatestActivity(): Activity | undefined {
    try {
      const db = DB.getInstance(DB.dbName)
      const sql = 'SELECT * FROM activity ORDER BY id DESC LIMIT 1'
      const latestActivity = db.queryOne<Activity>(sql)
      return latestActivity
    } catch (error) {
      console.error('❌ 获取最新的 activity 失败:', error)
      throw error
    }
  }
}
const activityService = new ActivityService()
export { activityService }
