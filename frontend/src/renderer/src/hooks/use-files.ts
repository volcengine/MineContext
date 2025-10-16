// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useState, useEffect, useCallback } from 'react'
import { typeIconMap } from '@renderer/utils/file'

export interface Document {
  name: string
  source: string
  status: string
  icon: string
  prompt: string
  filePath: string
}

export const useFiles = () => {
  const [analyzedDocs, setAnalyzedDocs] = useState<Document[]>([])

  const loadFiles = useCallback(async () => {
    const result = await window.fileService.getFiles()
    if (result.success && result.files) {
      const filesWithIcons = result.files
        .filter((file) => !file.name.startsWith('.')) // Filter out hidden files starting with .
        .map((file) => ({
          ...file,
          icon: typeIconMap[file.name.split('.').pop()]
        }))
      setAnalyzedDocs(filesWithIcons)
    }
  }, [])

  const saveFile = useCallback(async (fileName: string, fileData: Uint8Array) => {
    const result = await window.fileService.saveFile(fileName, fileData)
    return result
  }, [])

  useEffect(() => {
    loadFiles()
  }, [loadFiles])

  const addFile = useCallback((file: Document) => {
    setAnalyzedDocs((prev) => [...prev, file])
  }, [])

  return { analyzedDocs, addFile, loadFiles, saveFile }
}
