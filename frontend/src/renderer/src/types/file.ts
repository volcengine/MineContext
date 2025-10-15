// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

/**
 * @interface
 * @description File metadata interface
 */
export interface FileMetadata {
  /**
   * The unique identifier of the file
   */
  id: string
  /**
   * File name
   */
  name: string
  /**
   * The original name of the file (display name)
   */
  origin_name: string
  /**
   * File path
   */
  path: string
  /**
   * File size in bytes
   */
  size: number
  /**
   * File extension (including .)
   */
  ext: string
  /**
   * File type
   */
  type: FileTypes
  /**
   * ISO string of the file creation time
   */
  created_at: string
  /**
   * File count
   */
  count: number
  /**
   * The estimated token size of this file (optional)
   */
  tokens?: number
}

export interface FileType extends FileMetadata {}

export enum FileTypes {
  IMAGE = 'image',
  VIDEO = 'video',
  AUDIO = 'audio',
  TEXT = 'text',
  DOCUMENT = 'document',
  OTHER = 'other'
}
