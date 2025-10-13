// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useVaults } from '@renderer/hooks/useVault'
import { VaultTreeNode } from '@renderer/types'
import { isWithinSevenDays } from './time'

/**
 * 递归寻找指定ID的节点
 * @param node 搜索的根节点
 * @param targetId 目标节点ID
 * @returns 找到的节点，如果未找到返回null
 */
export const findNodeById = (node: VaultTreeNode, targetId: number): VaultTreeNode | null => {
  // 检查当前节点是否是目标节点
  if (node.id === targetId) {
    return node
  }

  // 递归搜索子节点
  if (node.children) {
    for (const child of node.children) {
      const found = findNodeById(child, targetId)
      if (found) {
        return found
      }
    }
  }

  return null
}

/**
 * 递归寻找指定ID节点的父节点
 * @param node 搜索的根节点
 * @param targetId 目标节点ID
 * @returns 找到的父节点，如果未找到返回null
 */
export const findParentNodeById = (node: VaultTreeNode, targetId: number): VaultTreeNode | null => {
  // 检查直接子节点中是否有目标节点
  if (node.children) {
    for (const child of node.children) {
      if (child.id === targetId) {
        return node // 返回父节点
      }
    }

    // 递归搜索子节点的子树
    for (const child of node.children) {
      const found = findParentNodeById(child, targetId)
      if (found) {
        return found
      }
    }
  }

  return null
}

/**
 * 递归删除指定ID的节点
 * @param node 搜索的根节点
 * @param targetId 目标节点ID
 * @returns 是否成功删除
 */
export const removeNodeById = (node: VaultTreeNode, targetId: number): boolean => {
  if (!node.children) {
    return false
  }

  // 检查直接子节点中是否有目标节点
  const index = node.children.findIndex(child => child.id === targetId)
  if (index !== -1) {
    node.children.splice(index, 1)
    return true
  }

  // 递归搜索子节点的子树
  for (const child of node.children) {
    if (removeNodeById(child, targetId)) {
      return true
    }
  }

  return false
}

/**
 * 递归收集所有节点的ID（包括子节点）
 * @param node 搜索的根节点
 * @returns 所有节点ID的数组
 */
export const collectAllNodeIds = (node: VaultTreeNode): number[] => {
  const ids = [node.id]

  if (node.children) {
    for (const child of node.children) {
      ids.push(...collectAllNodeIds(child))
    }
  }

  return ids
}

/**
 * 递归更新指定ID的节点
 * @param node 搜索的根节点
 * @param targetId 目标节点ID
 * @param updateFn 更新函数
 * @returns 是否成功更新
 */
export const updateNodeById = (
  node: VaultTreeNode,
  targetId: number,
  updateFn: (node: VaultTreeNode) => void
): boolean => {
  // 检查当前节点是否是目标节点
  if (node.id === targetId) {
    updateFn(node)
    return true
  }

  // 递归搜索子节点
  if (node.children) {
    for (const child of node.children) {
      if (updateNodeById(child, targetId, updateFn)) {
        return true
      }
    }
  }

  return false
}

/**
 * 递归遍历所有节点，对每个节点执行回调函数
 * @param node 搜索的根节点
 * @param callback 对每个节点执行的回调函数
 */
export const traverseNodes = (node: VaultTreeNode, callback: (node: VaultTreeNode) => void): void => {
  callback(node)

  if (node.children) {
    for (const child of node.children) {
      traverseNodes(child, callback)
    }
  }
}

/**
 * 获取节点路径（从根节点到目标节点的路径）
 * @param node 搜索的根节点
 * @param targetId 目标节点ID
 * @returns 节点路径数组，如果未找到返回null
 */
export const getNodePath = (node: VaultTreeNode, targetId: number): VaultTreeNode[] | null => {
  if (node.id === targetId) {
    return [node]
  }

  if (node.children) {
    for (const child of node.children) {
      const path = getNodePath(child, targetId)
      if (path) {
        return [node, ...path]
      }
    }
  }

  return null
}

/**
 * 递归排序树结构中的所有children，根据sort_order字段排序
 * @param node 要排序的根节点
 */
export const sortTreeByOrder = (node: VaultTreeNode): void => {
  // 如果当前节点有children，先对children进行排序
  if (node.children && node.children.length > 0) {
    // 根据sort_order排序，如果没有sort_order则默认为0
    node.children.sort((a, b) => {
      const orderA = a.sort_order ?? 0
      const orderB = b.sort_order ?? 0
      return orderA - orderB
    })

    // 递归对每个子节点进行排序
    node.children.forEach(child => {
      sortTreeByOrder(child)
    })
  }
}

export const removeMarkdownSymbols = (text: string) => {
    return text
        .replace(/^#{1,6}\s*/gm, '')
        .replace(/(\*\*|__)(.*?)\1/g, '$2')
        .replace(/(\*|_)(.*?)\1/g, '$2')
        .replace(/`{1,3}([^`]+)`{1,3}/g, '$1')
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
        .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
        .replace(/~~(.*?)~~/g, '$1')
        .replace(/^>\s*/gm, '')
        .replace(/^[-*+]\s+/gm, '')
        .replace(/^\d+\.\s+/gm, '')
        .trim()
}


export function formatVaultDate(date: Date | string | number): string {
  const d = new Date(date)
  const monthNames = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec'
  ]
  const month = monthNames[d.getMonth()]
  const day = d.getDate()
  const year = d.getFullYear()
  let hours = d.getHours()
  const minutes = d.getMinutes()
  const seconds = d.getSeconds()
  const ampm = hours >= 12 ? 'PM' : 'AM'
  hours = hours % 12
  hours = hours ? hours : 12 // the hour '0' should be '12'
  const strMinutes = minutes < 10 ? '0' + minutes : minutes
  const strSeconds = seconds < 10 ? '0' + seconds : seconds
  return `${month} ${day}, ${year} ${hours}:${strMinutes}:${strSeconds} ${ampm}`
}

export function getAllVaultsFlat(): VaultTreeNode[] {
  const { vaults } = useVaults()

  // 展平树结构
  const allDocuments: any[] = []
  traverseNodes(vaults, (node) => {
    // 排除根节点 (-1) 和文件夹 (is_folder === 1)
    if (node.id !== -1 && node.is_folder !== 1) {
      allDocuments.push(node)
    }
  })

  return allDocuments
}

export function getRecentVaults(): VaultTreeNode[] {
  const allDocuments = getAllVaultsFlat();
  const recentDocs: VaultTreeNode[] = []
  allDocuments.forEach(doc => {
   if (doc.updated_at && isWithinSevenDays(doc.updated_at)) {
     recentDocs.push(doc)
   }
  })

  return recentDocs
}

