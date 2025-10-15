// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { DB } from './Database' // Make sure to import the DB class

class ActivityService {
  /**
   * Get the latest Activity record from the database.
   * "Latest" is determined by sorting start_time in descending order.
   * @returns {Activity | undefined} Returns the latest Activity object, or undefined if there is no data in the table.
   */
  public getLatestActivity(): Activity | undefined {
    try {
      const db = DB.getInstance(DB.dbName)
      const sql = 'SELECT * FROM activity ORDER BY id DESC LIMIT 1'
      const latestActivity = db.queryOne<Activity>(sql)
      return latestActivity
    } catch (error) {
      console.error('❌ Failed to get the latest activity:', error)
      throw error
    }
  }
}
const activityService = new ActivityService()
export { activityService }
