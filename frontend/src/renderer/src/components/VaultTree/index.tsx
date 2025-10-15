// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { Dropdown, Menu, Space, Typography, Input, Message } from '@arco-design/web-react'
import { Tree, NodeRendererProps } from 'react-arborist'

import { useVaults } from '@renderer/hooks/useVault'
import { useNavigation } from '@renderer/hooks/useNavigation'
import { VaultTreeNode } from '@renderer/types'
import folderStrokedIcon from '/src/assets/icons/folder-stroked.svg'
import folderOpenIcon from '/src/assets/icons/folder-open.svg'
import fileIcon from '/src/assets/icons/file.svg'
import addIcon from '/src/assets/icons/add.svg'
import deleteIcon from '/src/assets/icons/delete.svg'
import renameIcon from '/src/assets/icons/rename.svg'
import './index.css'
import { useEffect, useRef, useState } from 'react'

const { Text, Ellipsis } = Typography

const Node = ({ node, dragHandle }: NodeRendererProps<VaultTreeNode>) => {
  const isFolder = node.data.is_folder === 1
  const { deleteVault, createFolder, addVault, getVaultPath } = useVaults()
  const { navigateToVault, isVaultActive } = useNavigation()
  const [visible, setVisible] = useState(false)
  const [isFolderHover, setIsFolderHover] = useState(false)

  const dropList = (
    <Menu
      onClickMenuItem={async (key) => {
        setVisible(false)
        if (key === 'rename') {
          node.edit()
        } else if (key === 'delete') {
          deleteVault(node.data.id)
        } else if (key === 'new-folder') {
          const path = getVaultPath(node.data.id)
          if (path && path.length >= 6) {
            Message.warning('Maximum folder depth of 5 levels reached.')
            return
          }
          await createFolder('Untitled', node.data.id)
          if (!node.isOpen) {
            node.toggle()
          }
        } else if (key === 'new-document') {
          await addVault({
            title: 'Untitled',
            content: '',
            parent_id: node.data.id
          })
          if (!node.isOpen) {
            node.toggle()
          }
        }
      }}>
      <Menu.Item key="rename" className="flex items-center">
        <img src={renameIcon} className="w-[16px]" style={{ marginRight: '6px' }} />
        Rename
      </Menu.Item>
      <Menu.Item key="delete" className="flex items-center">
        <img src={deleteIcon} className="w-[16px]" style={{ marginRight: '6px' }} />
        Delete
      </Menu.Item>
      {isFolder && (
        <>
          <Menu.Item key="new-folder" className="flex items-center">
            <img src={folderStrokedIcon} className="w-[16px]" style={{ marginRight: '6px' }} />
            New Folder
          </Menu.Item>
          <Menu.Item key="new-document" className="flex items-center">
            <img src={fileIcon} className="w-[16px]" style={{ marginRight: '6px' }} />
            New Document
          </Menu.Item>
        </>
      )}
    </Menu>
  )

  return (
    <Dropdown trigger="contextMenu" droplist={dropList} onVisibleChange={setVisible} popupVisible={visible}>
      <div
        style={{
          padding: '8px 12px',
          paddingLeft: `${node.level * 24 + 12}px`,
          borderRadius: '6px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          cursor: 'pointer',
          backgroundColor: !isFolder && isVaultActive(node.data.id) ? '#FFFFFF66' : 'transparent',
          fontWeight: !isFolder && isVaultActive(node.data.id) ? 500 : 400,
          transition: 'all 0.2s ease'
        }}
        ref={dragHandle}
        onClick={() => {
          if (isFolder) {
            node.toggle()
          } else {
            node.activate()
            navigateToVault(node.data.id)
          }
        }}
        onMouseEnter={(e) => {
          if (!(!isFolder && isVaultActive(node.data.id))) {
            e.currentTarget.style.backgroundColor = '#FFFFFF66'
          }
        }}
        onMouseLeave={(e) => {
          setIsFolderHover(false)
          if (!(!isFolder && isVaultActive(node.data.id))) {
            e.currentTarget.style.backgroundColor = 'transparent'
          }
        }}>
        {isFolder ? (
          <>
            <img
              onMouseEnter={() => setIsFolderHover(true)}
              onMouseLeave={() => setIsFolderHover(false)}
              src={node.isOpen || isFolderHover ? folderOpenIcon : folderStrokedIcon}
              alt="folder"
              className="w-[16px] rounded-[4px] shrink-0"
            />
          </>
        ) : (
          <img src={fileIcon} alt="file" className="w-[16px] rounded-[4px] shrink-0" />
        )}
        {node.isEditing ? (
          <Input
            autoFocus
            defaultValue={node.data.title}
            onBlur={() => node.reset()}
            className="h-[25px]"
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                node.submit(e.currentTarget.value)
              } else if (e.key === 'Escape') {
                node.reset()
              }
            }}
          />
        ) : (
          <Ellipsis
            className="text-[13px] overflow-auto"
            showTooltip
            rows={1}
            style={{
              fontWeight: !isFolder && isVaultActive(node.data.id) ? 500 : 400
            }}>
            {node.data.title}
          </Ellipsis>
        )}
      </div>
    </Dropdown>
  )
}

const Sidebar = () => {
  const { vaults: treeData, updateVaultPosition, createFolder, addVault, renameVault: onRenameVault } = useVaults()
  const { navigateToVault } = useNavigation()
  const treeContainerRef = useRef<HTMLDivElement>(null)
  const [treeDimensions, setTreeDimensions] = useState({ width: 200, height: 600 })

  useEffect(() => {
    if (treeContainerRef.current && treeContainerRef.current.clientWidth > 0) {
      setTreeDimensions({
        ...treeDimensions,
        width: treeContainerRef.current.clientWidth
      })
    }
  }, [treeData])

  const onRename = ({ id, name }: { id: string; name: string }) => {
    onRenameVault(Number(id), name)
  }
  const onMove = async ({
    dragIds,
    parentId,
    index
  }: {
    dragIds: string[]
    parentId: string | null
    index: number
  }) => {
    const newParentId = parentId === null || parentId === undefined ? -1 : Number(parentId)
    for (const id of dragIds) {
      await updateVaultPosition(Number(id), { parent_id: newParentId, sort_order: index })
    }
  }

  const handleMenuClick = async (key: string) => {
    if (key === 'new-folder') {
      await createFolder('Untitled')
    } else if (key === 'new-document') {
      await addVault({ title: 'Untitled', content: '' })
    }
  }

  const menu = (
    <Menu onClickMenuItem={handleMenuClick} className="w-[180px] text-[12px]">
      <Menu.Item key="new-folder" className="flex">
        <img src={folderStrokedIcon} style={{ width: '16px', marginRight: '6px' }} />
        New Folder
      </Menu.Item>
      <Menu.Item key="new-document" className="flex">
        <img src={fileIcon} style={{ width: '16px', marginRight: '6px' }} />
        New Document
      </Menu.Item>
    </Menu>
  )

  return (
    <div className="flex-1 flex flex-col min-h-[0]" style={{ marginTop: 12 }}>
      <div className="flex flex-col flex-1 min-h-[0]">
        {/* Vault notes section */}
        <div className="px-[12px] shrink-0">
          <Space direction="vertical" size={8} className="w-full">
            <div className="flex items-center justify-between">
              <Text className="text-[12px]" style={{ color: '#6E718C' }}>
                Creation
              </Text>
              <div className="flex justify-end gap-[8px] flex-1 items-center">
                <Dropdown droplist={menu} trigger="click">
                  <img src={addIcon} alt="add" className="w-[12px] cursor-pointer" />
                </Dropdown>
              </div>
            </div>
          </Space>
        </div>

        {/* Modern tree structure */}
        <div className="note-tree-container flex-1 min-h-[0] font-[12px]" ref={treeContainerRef}>
          {treeDimensions.height > 0 && (
            <Tree
              idAccessor={(data) => data.id.toString()}
              data={treeData?.children || []}
              onRename={onRename}
              onMove={onMove}
              width={treeDimensions.width}
              height={treeDimensions.height}
              rowHeight={32}
              indent={0}
              onActivate={(node) => {
                if (node.data.is_folder !== 1) {
                  navigateToVault(node.data.id)
                }
              }}>
              {Node}
            </Tree>
          )}
        </div>
      </div>
    </div>
  )
}

export default Sidebar
