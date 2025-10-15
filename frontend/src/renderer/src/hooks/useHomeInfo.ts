// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useState, useEffect } from 'react'

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
  status: number
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
      console.log('addTask', res)
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

  useEffect(() => {
    const fetchData = async () => {
      try {
        const daily = await window.dbAPI.getAllVaults('daily')
        setDailySummary(daily)

        const weekly = await window.dbAPI.getAllVaults('weekly')
        setWeeklySummary(weekly)

        const today = new Date()
        const startOfDay = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 0, 0, 0)
        const tasks = await window.dbAPI.getTasks(startOfDay.toISOString())
        setTasks(tasks)
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
    addTask
  }
}
