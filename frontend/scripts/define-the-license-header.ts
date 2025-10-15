// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0
import fs from 'fs'
import path from 'path'

const jsHeader = `// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0
`

const cssHeader = `/*
 * Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
 * SPDX-License-Identifier: Apache-2.0
 */
`

const jsExtensions = ['.ts', '.tsx', '.js', '.jsx']
const cssExtensions = ['.css', '.less', '.scss']

const projectRoot = path.resolve(__dirname, '..')
const excludedDirs = ['node_modules', 'dist', 'build', 'venv', '.vscode', 'externals', 'resources', 'coverage']

const addLicenseHeader = (filePath: string) => {
  try {
    const content = fs.readFileSync(filePath, 'utf-8')
    const ext = path.extname(filePath)

    // Check if header already exists to avoid duplication
    if (content.includes('SPDX-License-Identifier: Apache-2.0')) {
      return
    }

    let header
    if (jsExtensions.includes(ext)) {
      header = jsHeader
    } else if (cssExtensions.includes(ext)) {
      header = cssHeader
    } else {
      return // Should not happen if called correctly
    }

    const newContent = header + '\n' + content
    fs.writeFileSync(filePath, newContent, 'utf-8')
    console.log(`Added license header to: ${path.relative(projectRoot, filePath)}`)
  } catch (error) {
    console.error(`Failed to process file ${filePath}:`, error)
  }
}

const traverseDirectory = (dir: string) => {
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true })
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name)
      if (entry.isDirectory()) {
        if (!excludedDirs.includes(entry.name) && !entry.name.startsWith('.')) {
          traverseDirectory(fullPath)
        }
      } else {
        // Exclude the script file itself
        if (fullPath === __filename) {
          continue
        }
        const ext = path.extname(entry.name)
        if (jsExtensions.includes(ext) || cssExtensions.includes(ext)) {
          addLicenseHeader(fullPath)
        }
      }
    }
  } catch (error) {
    console.error(`Could not read directory ${dir}:`, error)
  }
}

const main = () => {
  const targetDirs = process.argv.slice(2)

  console.log('Starting to add license headers...')

  if (targetDirs.length > 0) {
    console.log(`Processing specified directories: ${targetDirs.join(', ')}`)
    for (const dir of targetDirs) {
      const targetPath = path.resolve(process.cwd(), dir)
      if (fs.existsSync(targetPath) && fs.lstatSync(targetPath).isDirectory()) {
        traverseDirectory(targetPath)
      } else {
        console.warn(`Warning: Directory not found or not a directory, skipping: ${targetPath}`)
      }
    }
  } else {
    console.log(`Processing project root: ${projectRoot}`)
    traverseDirectory(projectRoot)
  }

  console.log('Finished adding license headers.')
}

main()
