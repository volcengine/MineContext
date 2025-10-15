// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { formatRelativeTime } from '@renderer/utils/time'
import docIcon from '@renderer/assets/icons/doc-icon.svg'
import { VaultTreeNode } from '@renderer/types'
import { useNavigation } from '@renderer/hooks/useNavigation'
import { CardLayout } from '@renderer/pages/home/components/layout'

interface DocColumnBoxProps {
  vaultsList: VaultTreeNode[]
}

interface DocColumnProps {
  vault: VaultTreeNode
}

const DocColumn = ({ vault }: DocColumnProps) => {
  const { title, updated_at } = vault
  const { navigateToVault } = useNavigation()

  const handleNavigateToVault = () => {
    navigateToVault(vault.id)
  }
  return (
    <div className="group flex items-center justify-between p-1 rounded transition-all duration-200 bg-white w-full h-[32px] hover:bg-[#F7F8FD]">
      <div className="flex items-center gap-2">
        {/* Left side: icon + title */}
        <div className="flex items-center gap-[6px]">
          <img src={docIcon} alt="doc icon" />
          <span className="text-[var(--text-color-text-1)] font-roboto text-[13px] font-normal leading-[22px] tracking-[0.039px]">
            {title}
          </span>
        </div>
        {/* Edit time - hidden by default, shown on hover */}
        {updated_at && (
          <span className="flex flex-1 text-[#AEAFC2] font-roboto items-center text-[11px] font-normal leading-[22px] tracking-[0.033px] opacity-0 group-hover:opacity-100">
            {formatRelativeTime(updated_at)}
          </span>
        )}
      </div>

      {/* Right side: shows "Edit time + View button" on hover */}
      <div className="flex items-center">
        {/* View button - hidden by default, shown on hover */}
        <button
          className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 text-[#7075FF] font-pingfang-sc text-[12px] font-medium leading-[20px] tracking-[0.036px] cursor-pointer"
          onClick={handleNavigateToVault}>
          View
        </button>
      </div>
    </div>
  )
}

const DocColumnsCard: React.FC<DocColumnBoxProps> = ({ vaultsList }) => {
  return (
    <CardLayout title="Recent creation" emptyText="No creation in the last 7 days. " isEmpty={vaultsList.length === 0}>
      <div className="flex flex-col items-start gap-[4px] self-stretch">
        {vaultsList.map((vault) => (
          <DocColumn key={vault.id} vault={vault} />
        ))}
      </div>
    </CardLayout>
  )
}

export { DocColumnsCard }
