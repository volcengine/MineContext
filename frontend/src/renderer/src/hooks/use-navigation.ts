// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '@renderer/store'
import { setActiveMainTab, setActiveVault, clearActiveVault, initializeFromRoute } from '@renderer/store/navigation'

export const useNavigation = () => {
  const dispatch = useAppDispatch()
  const location = useLocation()
  const navigate = useNavigate()

  const { activeNavigationType, activeMainTab, activeVaultId } = useAppSelector((state) => state.navigation)

  // 初始化时根据当前路由设置导航状态
  useEffect(() => {
    dispatch(
      initializeFromRoute({
        pathname: location.pathname,
        search: location.search
      })
    )
  }, [location.pathname, location.search, dispatch])

  // 导航到主页面
  const navigateToMainTab = (tabKey: string, path: string) => {
    dispatch(setActiveMainTab(tabKey))
    navigate(path)
  }

  // 导航到 Vault 页面
  const navigateToVault = (vaultId: number) => {
    dispatch(setActiveVault(vaultId))
    navigate(`/vault?id=${encodeURIComponent(vaultId)}`)
  }

  // 清除 Vault 选择状态
  const clearVaultSelection = () => {
    dispatch(clearActiveVault())
  }

  // 检查主导航项是否激活
  const isMainTabActive = (tabKey: string) => {
    return activeNavigationType === 'main' && activeMainTab === tabKey
  }

  // 检查 Vault 是否激活
  const isVaultActive = (vaultId: number) => {
    return activeNavigationType === 'vault' && activeVaultId === vaultId
  }

  // 检查是否在 Vault 页面
  const isInVaultArea = () => {
    return activeNavigationType === 'vault'
  }

  return {
    // 状态
    activeNavigationType,
    activeMainTab,
    activeVaultId,

    // 导航方法
    navigateToMainTab,
    navigateToVault,
    clearVaultSelection,

    // 检查方法
    isMainTabActive,
    isVaultActive,
    isInVaultArea
  }
}
