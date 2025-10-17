// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

'use client'

import { cn } from '@renderer/lib/utils'
import { type ComponentProps, memo } from 'react'
import { Streamdown } from 'streamdown'

type ResponseProps = ComponentProps<typeof Streamdown>

export const Response = memo(
  ({ className, ...props }: ResponseProps) => (
    <Streamdown className={cn('size-full [&>*:first-child]:mt-0 [&>*:last-child]:mb-0', className)} {...props} />
  ),
  (prevProps, nextProps) => prevProps.children === nextProps.children
)

Response.displayName = 'Response'
