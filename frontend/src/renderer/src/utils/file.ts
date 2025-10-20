// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import pdfIcon from '@renderer/assets/images/files/pdf.png'
import pptIcon from '@renderer/assets/images/files/ppt.png'
import docIcon from '@renderer/assets/images/files/doc.png'
import xlsxIcon from '@renderer/assets/images/files/xlsx.png'
import csvIcon from '@renderer/assets/images/files/csv.png'
import txtIcon from '@renderer/assets/images/files/txt.png'
import markdownIcon from '@renderer/assets/images/files/markdown.png'
import faqIcon from '@renderer/assets/images/files/faq.png'

export const typeIconMap = {
  pdf: pdfIcon,
  ppt: pptIcon,
  pptx: pptIcon,
  doc: docIcon,
  docx: docIcon,
  xls: xlsxIcon,
  xlsx: xlsxIcon,
  csv: csvIcon,
  txt: txtIcon,
  md: markdownIcon,
  markdown: markdownIcon,
  faq: faqIcon
}

/**
 * Convert file system path to file:// URL
 * Handles both Windows and macOS/Linux paths correctly
 * @param filePath - The file system path (can use either / or \ as separator)
 * @returns Properly formatted file:// URL
 */
export function pathToFileURL(filePath: string): string {
  // Normalize path separators to forward slashes
  const normalizedPath = filePath.replace(/\\/g, '/')

  // Check if it's a Windows absolute path (e.g., C:/Users/...)
  if (/^[a-zA-Z]:/.test(normalizedPath)) {
    // Windows: file:///C:/Users/...
    return `file:///${normalizedPath}`
  }

  // macOS/Linux: file:///Users/... or file:///home/...
  if (normalizedPath.startsWith('/')) {
    return `file://${normalizedPath}`
  }

  // Fallback: assume it's already a relative path or URL
  return normalizedPath
}
