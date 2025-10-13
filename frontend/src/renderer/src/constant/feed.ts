// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

export enum PushDataTypes {
  TIP_GENERATED = 'tip',
  TODO_GENERATED = 'todo',
  ACTIVITY_GENERATED = 'activity',
  DAILY_SUMMARY_GENERATED = 'daily_summary',
  WEEKLY_SUMMARY_GENERATED = 'weekly_summary',
  SYSTEM_STATUS = 'system_status',
  DOCUMENT = 'document'
}
export const enum TaskUrgency {
  High = 2,
  Medium = 1,
  Low = 0,
  Done = -1
}
export const TODO_LIST_STATUS = {
  Create: 'create',
  Edit: 'edit'
}
