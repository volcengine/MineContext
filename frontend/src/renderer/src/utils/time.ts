// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import dayjs from 'dayjs';
import isBetween from 'dayjs/plugin/isBetween';
dayjs.extend(isBetween);

// Format time
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

// Format date
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


// Calculate the elapsed time based on the date string and the current time, with precision to days/hours and minutes
export const formatRelativeTime = (dateString: string): string => {
  const now = dayjs();
  const time = dayjs(dateString);
  const diffInMinutes = now.diff(time, 'minute');

  if (diffInMinutes < 1) {
    return 'Just now';
  }

  // Calculate the difference in days
  const days = Math.floor(diffInMinutes / (24 * 60));

  // If it's more than 7 days, display the specific date (month/day hour:minute)
  if (days >= 7) {
    return time.format('MM/DD HH:mm');
  }

  // If it's more than 24 hours but less than 7 days, display as N days ago
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

// Format '2025-05-02' to determine if the date is within the last seven days
export const isWithinSevenDays = (dateString: string): boolean => {
    const targetDate = dayjs(dateString); // Parse as a Day.js object

    // Calculate the start time of seven days ago (00:00:00)
    const sevenDaysAgo = dayjs().subtract(7, 'day').startOf('day');
    // Calculate the end time of the current time (23:59:59)
    const nowEnd = dayjs().endOf('day');

    // Determine if the target date is within the [seven days ago, now] interval (inclusive)
    const isWithinSevenDays = targetDate.isBetween(
      sevenDaysAgo,
      nowEnd,
      'day', // Compare by day (ignoring time differences)
      '[]'  // Include the start and end of the interval
    );
    return isWithinSevenDays;
}

// Export vault-related utility functions
export * from './vault'
