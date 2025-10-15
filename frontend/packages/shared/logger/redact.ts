// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

// NDJSON Hook: Normalize message.data:any[] to a single line of JSON
export type Json = Record<string, any>
const redact = (x: any): any => {
  if (!x || typeof x !== 'object') return x
  const c = JSON.parse(JSON.stringify(x))
  if (c.password) c.password = '***'
  if (c.token) c.token = '***'
  if (c.headers?.authorization) c.headers.authorization = '***'
  return c
}
export { redact }
