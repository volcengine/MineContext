// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { is } from '@electron-toolkit/utils'

export const isLinux = process.platform === 'linux'
export const isMac = process.platform === 'darwin'
export const isWin = process.platform === 'win32'
export const isDev = process.env.NODE_ENV === 'development' || is.dev
export const isPortable = isWin && 'PORTABLE_EXECUTABLE_DIR' in process.env
