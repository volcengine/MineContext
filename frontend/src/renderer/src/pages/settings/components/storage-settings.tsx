// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { FC, useEffect, useState } from 'react'
import { Form, Slider, Switch, Typography, Statistic } from '@arco-design/web-react'
import { IconStorage } from '@arco-design/web-react/icon'

const FormItem = Form.Item
const { Text } = Typography

interface StorageSettingsProps {
  form: any
}

const StorageSettings: FC<StorageSettingsProps> = ({ form }) => {
  const [storageStats, setStorageStats] = useState<{
    usedSizeMb: number
    totalFileCount: number
  }>({
    usedSizeMb: 0,
    totalFileCount: 0
  })

  // Get storage statistics from main process
  useEffect(() => {
    const fetchStats = async () => {
      try {
        // Call IPC to get actual storage stats
        const stats = await window.electron.ipcRenderer.invoke('storage:get-stats')
        if (stats.success) {
          setStorageStats({
            usedSizeMb: stats.usedSizeMb || 0,
            totalFileCount: stats.fileCount || 0
          })
        }
      } catch (error) {
        console.error('Failed to fetch storage stats:', error)
      }
    }

    fetchStats()
    // Refresh stats every 30 seconds
    const interval = setInterval(fetchStats, 30000)
    return () => clearInterval(interval)
  }, [])

  const retentionDays = Form.useWatch('retention_days', form) || 15
  const maxStorageSizeMb = Form.useWatch('max_storage_size_mb', form) || 5000

  return (
    <div className="flex flex-col gap-6 mt-6">
      {/* Storage Statistics */}
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-4">
          <IconStorage className="text-lg" />
          <Text className="text-base font-medium">Storage Statistics</Text>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <Statistic title="Used Space" value={storageStats.usedSizeMb.toFixed(2)} suffix="MB" precision={2} />
          <Statistic
            title="Max Space"
            value={maxStorageSizeMb === 0 ? 'Unlimited' : `${maxStorageSizeMb} MB`}
            groupSeparator
          />
          <Statistic title="File Count" value={storageStats.totalFileCount} groupSeparator />
        </div>
        {maxStorageSizeMb > 0 && (
          <div className="mt-3">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Usage Rate</span>
              <span>{((storageStats.usedSizeMb / maxStorageSizeMb) * 100).toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all"
                style={{
                  width: `${Math.min((storageStats.usedSizeMb / maxStorageSizeMb) * 100, 100)}%`
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Retention Days Setting */}
      <div className="flex flex-col gap-2">
        <Text className="text-[#0B0B0F] font-roboto text-base font-normal leading-[22px]">Retention Time</Text>
        <Text type="secondary" className="text-sm">
          Automatically delete screenshots files that exceed the specified number of days
        </Text>
        <FormItem
          field="retention_days"
          className="[&_.arco-form-item]: !mb-0 mt-2"
          rules={[{ required: true, message: 'Please set the retention days' }]}
          requiredSymbol={false}>
          <Slider
            min={7}
            max={90}
            marks={{
              7: '7 days',
              30: '30 days',
              60: '60 days',
              90: '90 days'
            }}
            style={{ width: '574px' }}
          />
        </FormItem>
        <div className="flex justify-between items-center" style={{ width: '574px' }}>
          <Text type="secondary" className="text-xs">
            current setting: {retentionDays} days
          </Text>
          <Text type="secondary" className="text-xs">
            Expected to retain approximately {((retentionDays * storageStats.totalFileCount) / 15).toFixed(0)}{' '}
            screenshots
          </Text>
        </div>
      </div>

      {/* Max Storage Size Setting */}
      <div className="flex flex-col gap-2">
        <Text className="text-[#0B0B0F] font-roboto text-base font-normal leading-[22px]">Max Storage Space</Text>
        <Text type="secondary" className="text-sm">
          Limit the maximum disk space used by screenshots (0 means unlimited)
        </Text>
        <FormItem
          field="max_storage_size_mb"
          className="[&_.arco-form-item]: !mb-0 mt-2"
          rules={[{ required: true, message: 'Please set the max storage space' }]}
          requiredSymbol={false}>
          <Slider
            min={0}
            max={20000}
            step={500}
            marks={{
              0: 'Unlimited',
              5000: '5GB',
              10000: '10GB',
              15000: '15GB',
              20000: '20GB'
            }}
            style={{ width: '574px' }}
          />
        </FormItem>
        <div className="flex justify-between items-center" style={{ width: '574px' }}>
          <Text type="secondary" className="text-xs">
            current setting:{' '}
            {maxStorageSizeMb === 0
              ? 'Unlimited'
              : `${maxStorageSizeMb} MB (${(maxStorageSizeMb / 1024).toFixed(1)} GB)`}
          </Text>
          {maxStorageSizeMb > 0 && storageStats.usedSizeMb > maxStorageSizeMb * 0.8 && (
            <Text type="warning" className="text-xs">
              ⚠️ Storage space is about to run out
            </Text>
          )}
        </div>
      </div>

      {/* Auto Cleanup Setting */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between" style={{ width: '574px' }}>
          <div>
            <Text className="text-[#0B0B0F] font-roboto text-base font-normal leading-[22px]">Automatic Cleanup</Text>
            <Text type="secondary" className="text-sm block mt-1">
              Automatically clean up expired files every day
            </Text>
          </div>
          <FormItem
            field="auto_cleanup_enabled"
            className="[&_.arco-form-item]: !mb-0"
            requiredSymbol={false}
            triggerPropName="checked">
            <Switch />
          </FormItem>
        </div>
      </div>
    </div>
  )
}

export default StorageSettings
