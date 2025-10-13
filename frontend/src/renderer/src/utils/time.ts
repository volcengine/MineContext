// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import dayjs from 'dayjs';
import isBetween from 'dayjs/plugin/isBetween';
dayjs.extend(isBetween);

// 格式化时间
export const formatTime = (date: Date | number | string) => {
  if (typeof date === 'string' || typeof date === 'number') {
    date = new Date(date)
  }
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

// 格式化日期
export const formatDate = (date: Date) => {
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

export const timestampToISODateString = (timestamp: number): string => {
    const date = new Date(timestamp)
    return date.toISOString().slice(0, 10).replace(/-/g, '')
}

export const timeToISOTimeString = (time: number | Date): string => {
    if (typeof time === 'number') {
        time = new Date(time)
    }
    const year = time.getFullYear();
    const month = time.getMonth();
    const day = time.getDate();
    const hour = time.getHours();
    const minute = time.getMinutes();
    const second = time.getSeconds();
    return new Date(Date.UTC(year, month, day, hour, minute, second, 0)).toISOString();
    // const endTime = new Date(Date.UTC(year, month, day + 1, 0, 0, 0, 0)).toISOString();
}


// 根据日期字符串以及现在的时间计算已经过去的时间，精度为天/小时与分钟
export const formatRelativeTime = (dateString: string): string => {
  const now = dayjs();
  const time = dayjs(dateString);
  const diffInMinutes = now.diff(time, 'minute');

  if (diffInMinutes < 1) {
    return 'Just now';
  }

  // 计算天数差
  const days = Math.floor(diffInMinutes / (24 * 60));

  // 超过7天显示具体日期（月/日 时:分）
  if (days >= 7) {
    return time.format('MM/DD HH:mm');
  }

  // 超过24小时但不足7天显示为 N days ago
  if (days > 0) {
    return `${days} day${days > 1 ? 's' : ''} ago`;
  }

  const hours = Math.floor(diffInMinutes / 60);
  const minutes = diffInMinutes % 60;

  if (hours > 0) {
    return `${hours}h ago`;
  } else {
    return `${minutes}m ago`;
  }
};

// 格式 '2025-05-02' 判断日期是否为最近七天内
export const isWithinSevenDays = (dateString: string): boolean => {
    const targetDate = dayjs(dateString); // 解析为 Day.js 对象

    // 计算七天前的起始时间（00:00:00）
    const sevenDaysAgo = dayjs().subtract(7, 'day').startOf('day');
    // 计算当前时间的结束时间（23:59:59）
    const nowEnd = dayjs().endOf('day');

    // 判断目标日期是否在 [七天前, 现在] 区间内（包含两端）
    const isWithinSevenDays = targetDate.isBetween(
      sevenDaysAgo,
      nowEnd,
      'day', // 以「天」为单位比较（忽略时分秒差异）
      '[]'  // 包含区间的开始和结束
    );
    return isWithinSevenDays;
}

// 导出vault相关工具函数
export * from './vault'
