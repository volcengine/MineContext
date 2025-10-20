// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useVaults } from '@renderer/hooks/use-vault'
import { VaultTreeNode } from '@renderer/types'
import { isWithinSevenDays } from './time'
import dayjs from 'dayjs'

/**
 * Recursively find a node with the specified ID
 * @param node The root node to search from
 * @param targetId The ID of the target node
 * @returns The found node, or null if not found
 */
export const findNodeById = (node: VaultTreeNode, targetId: number): VaultTreeNode | null => {
  // Check if the current node is the target node
  if (node.id === targetId) {
    return node
  }

  // Recursively search child nodes
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
 * Recursively find the parent node of a node with the specified ID
 * @param node The root node to search from
 * @param targetId The ID of the target node
 * @returns The found parent node, or null if not found
 */
export const findParentNodeById = (node: VaultTreeNode, targetId: number): VaultTreeNode | null => {
  // Check if any of the direct children is the target node
  if (node.children) {
    for (const child of node.children) {
      if (child.id === targetId) {
        return node // Return the parent node
      }
    }

    // Recursively search the subtrees of the children
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
 * Recursively delete a node with the specified ID
 * @param node The root node to search from
 * @param targetId The ID of the target node
 * @returns Whether the deletion was successful
 */
export const removeNodeById = (node: VaultTreeNode, targetId: number): boolean => {
  if (!node.children) {
    return false
  }

  // Check if any of the direct children is the target node
  const index = node.children.findIndex((child) => child.id === targetId)
  if (index !== -1) {
    node.children.splice(index, 1)
    return true
  }

  // Recursively search the subtrees of the children
  for (const child of node.children) {
    if (removeNodeById(child, targetId)) {
      return true
    }
  }

  return false
}

/**
 * Recursively collect the IDs of all nodes (including children)
 * @param node The root node to search from
 * @returns An array of all node IDs
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
 * Recursively update a node with the specified ID
 * @param node The root node to search from
 * @param targetId The ID of the target node
 * @param updateFn The update function
 * @returns Whether the update was successful
 */
export const updateNodeById = (
  node: VaultTreeNode,
  targetId: number,
  updateFn: (node: VaultTreeNode) => void
): boolean => {
  // Check if the current node is the target node
  if (node.id === targetId) {
    updateFn(node)
    return true
  }

  // Recursively search child nodes
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
 * Recursively traverse all nodes and execute a callback function on each node
 * @param node The root node to search from
 * @param callback The callback function to execute on each node
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
 * Get the path of a node (from the root node to the target node)
 * @param node The root node to search from
 * @param targetId The ID of the target node
 * @returns An array of nodes in the path, or null if not found
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
 * Recursively sort all children in the tree structure by the sort_order field
 * @param node The root node to sort
 */
export const sortTreeByOrder = (node: VaultTreeNode): void => {
  // If the current node has children, sort them first
  if (node.children && node.children.length > 0) {
    // Sort by sort_order, defaulting to 0 if it doesn't exist
    node.children.sort((a, b) => {
      const orderA = a.sort_order ?? 0
      const orderB = b.sort_order ?? 0
      return orderA - orderB
    })

    // Recursively sort each child node
    node.children.forEach((child) => {
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
  return dayjs(date).format('MMM D, YYYY h:mm:ss A')
}

export function getAllVaultsFlat(): VaultTreeNode[] {
  const { vaults } = useVaults()

  // Flatten the tree structure
  const allDocuments: any[] = []
  traverseNodes(vaults, (node) => {
    // Exclude the root node (-1) and folders (is_folder === 1)
    if (node.id !== -1 && node.is_folder !== 1) {
      allDocuments.push(node)
    }
  })

  return allDocuments
}

export function getRecentVaults(): VaultTreeNode[] {
  const allDocuments = getAllVaultsFlat()
  const recentDocs: VaultTreeNode[] = []
  allDocuments.forEach((doc) => {
    if (doc.updated_at && isWithinSevenDays(doc.updated_at)) {
      recentDocs.push(doc)
    }
  })

  return recentDocs
}
