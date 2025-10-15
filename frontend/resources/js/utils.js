// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

export function getQueryParam(paramName) {
  const url = new URL(window.location.href)
  const params = new URLSearchParams(url.search)
  return params.get(paramName)
}
