// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

export const isFocused = () => {
  return document.hasFocus()
}

export const isOnHomePage = () => {
  return window.location.hash === '#/' || window.location.hash === '#' || window.location.hash === ''
}
