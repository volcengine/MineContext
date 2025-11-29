// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useState, useEffect } from 'react'
import dayjs, { Dayjs } from 'dayjs'
import { useRequest } from 'ahooks'

interface Vault {
  id: number
  title: string
  content: string
  summary: string
  tags: string
  parent_id: number | null
  is_folder: number
  is_deleted: number
  created_at: string
  updated_at: string
  sort_order: number
}

export interface Task {
  id: number
  content: string
  status: number // 0: not done, 1: done
  start_time: string
  end_time: string
  urgency: number
}

interface Tip {
  id: number
  content: string
  created_at: string
}

export const useHomeInfo = () => {
  const [dailySummary, setDailySummary] = useState<Vault[]>([])
  const [weeklySummary, setWeeklySummary] = useState<Vault[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [tips, setTips] = useState<Tip[]>([])

  const addTask = async (
    taskData: Partial<{ content?: string; status?: number; start_time?: string; end_time?: string; urgency?: number }>
  ) => {
    try {
      const res = await window.dbAPI.addTask(taskData)
      setTasks((prevTasks) => [
        ...prevTasks,
        {
          id: res.lastInsertRowid || -1,
          content: taskData.content || '',
          status: taskData.status || 0,
          start_time: taskData.start_time || '',
          end_time: taskData.end_time || '',
          urgency: taskData.urgency || 0
        }
      ])
      return res.lastInsertRowid
    } catch (error) {
      console.error('Failed to add task:', error)
      throw error
    }
  }

  const toggleTaskStatus = async (id: number) => {
    try {
      await window.dbAPI.toggleTaskStatus(id)
      setTasks((prevTasks) => prevTasks.map((task) => (task.id === id ? { ...task, status: 1 - task.status } : task)))
    } catch (error) {
      console.error('Failed to toggle task status:', error)
    }
  }

  const updateTask = async (
    id: number,
    taskData: Partial<{ content: string; urgency: number; start_time: string; end_time: string }>
  ) => {
    try {
      await window.dbAPI.updateTask(id, taskData)
      setTasks((prevTasks) => prevTasks.map((task) => (task.id === id ? { ...task, ...taskData } : task)))
    } catch (error) {
      console.error('Failed to update task:', error)
      throw error
    }
  }

  const deleteTask = async (id: number) => {
    try {
      await window.dbAPI.deleteTask(id)
      setTasks((prevTasks) => prevTasks.filter((task) => task.id !== id))
    } catch (error) {
      console.error('Failed to delete task:', error)
      throw error
    }
  }

  const { runAsync: fetchTasks } = useRequest<Task[] | undefined, any>(
    async (day: Dayjs) => {
      // Get tasks for the entire day
      const startOfDay = day.startOf('day').toISOString()
      const endOfDay = day.add(1, 'day').startOf('day').toISOString()
      return await window.dbAPI.getTasks(startOfDay, endOfDay)
    },
    {
      manual: true
    }
  )

  useEffect(() => {
    const fetchData = async () => {
      try {
        const daily = await window.dbAPI.getVaultsByDocumentType('daily')
        setDailySummary(daily)

        const weekly = await window.dbAPI.getVaultsByDocumentType('weekly')
        setWeeklySummary(weekly)

        const tasks = await fetchTasks(dayjs())
        setTasks(tasks || [])
        const allTips = await window.dbAPI.getAllTips()
        setTips(allTips.sort((a, b) => b.id - a.id))
      } catch (error) {
        console.error('Error fetching home info:', error)
      }
    }

    fetchData()
  }, [])

  return {
    dailySummary,
    weeklySummary,
    tasks,
    tips,
    toggleTaskStatus,
    updateTask,
    deleteTask,
    addTask,
    fetchTasks
  }
}
