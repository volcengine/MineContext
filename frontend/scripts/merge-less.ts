// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import fs from 'fs'
import path from 'path'

const mainLessFile = path.resolve(__dirname, '../src/renderer/src/assets/theme/component.less')
const outputFile = path.resolve(__dirname, '../src/renderer/src/assets/theme/components.less')

const mergeLessFiles = () => {
  try {
    console.log(`Reading main file: ${mainLessFile}`)
    const mainContent = fs.readFileSync(mainLessFile, 'utf-8')

    const importRegex = /@import\s+"(.+?)";/g
    let match
    const importedFiles: string[] = []

    while ((match = importRegex.exec(mainContent)) !== null) {
      // match[1] will be like "./components/Alert/index.less"
      const relativePath = match[1]
      // We need to resolve it relative to the main less file's directory
      const importFullPath = path.resolve(path.dirname(mainLessFile), relativePath)
      importedFiles.push(importFullPath)
    }

    if (importedFiles.length === 0) {
      console.log('No @import statements found. Nothing to merge.')
      return
    }

    console.log(`Found ${importedFiles.length} files to merge.`)

    let mergedContent = `/*
 * This file is auto-generated. Do not edit directly.
 * It is created by the merge-less.ts script.
 *
 * Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
 * SPDX-License-Identifier: Apache-2.0
 */

`

    for (const filePath of importedFiles) {
      try {
        const fileContent = fs.readFileSync(filePath, 'utf-8')
        const relativeFilePath = path.relative(path.dirname(outputFile), filePath)

        mergedContent += `/* --- Start of ${relativeFilePath} --- */\n\n`
        mergedContent += fileContent
        mergedContent += `\n\n/* --- End of ${relativeFilePath} --- */\n\n`
        console.log(`+ Appended ${relativeFilePath}`)
      } catch (readError) {
        console.error(`- Could not read file: ${filePath}`, readError)
      }
    }

    fs.writeFileSync(outputFile, mergedContent, 'utf-8')
    console.log(`\n✅ Successfully merged ${importedFiles.length} files into ${outputFile}`)
  } catch (error) {
    console.error('An error occurred during the merge process:', error)
  }
}

mergeLessFiles()
