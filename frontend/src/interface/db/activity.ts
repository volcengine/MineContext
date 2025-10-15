// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

/**
 * TypeScript type definition corresponding to the 'activity' table.
 * Field types map one-to-one with SQL types:
 * - INTEGER → number (auto-incrementing ID is a number)
 * - TEXT → string (text content)
 * - JSON → generic object type (Record<string, any>, can be refined if the structure is known)
 * - DATETIME → string (datetime string, usually in ISO format like '2025-09-28 12:00:00')
 */
interface Activity {
  // Auto-incrementing primary key (integer)
  id: number
  // Activity title (text)
  title: string
  // Activity content (text)
  content: string
  // Resource information (JSON format, stores an object)
  resources: string // Can be replaced with { files: string[]; link?: string; ... } if the structure is known
  // Start time (datetime string)
  start_time: string
  // End time (datetime string)
  end_time: string
  // Metadata (JSON format, stores extra information)
  metadata: string // Similarly, can be refined based on the actual structure, e.g., { author: string; status: 'draft' | 'published' }
}
