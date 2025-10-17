// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

const fs = require('fs')
const path = require('path')

console.log('📦 Copying pre-built backend executable...')

// Setup paths
const backendDir = path.join(__dirname, '..', 'backend')
const sourceDir = path.join(__dirname, '..', '..')
const executableName = process.platform === 'win32' ? 'main.exe' : 'main'
const sourceExecutablePath = path.join(sourceDir, 'dist', executableName)
const destExecutablePath = path.join(backendDir, executableName)

// Clean up existing backend directory
if (fs.existsSync(backendDir)) {
  console.log('🧹 Cleaning up existing backend directory...')
  fs.rmSync(backendDir, { recursive: true, force: true })
}

// Ensure backend directory exists
fs.mkdirSync(backendDir, { recursive: true })

// Check if pre-built executable exists
if (!fs.existsSync(sourceExecutablePath)) {
  console.error(`❌ Pre-built executable not found at: ${sourceExecutablePath}`)
  console.log('')
  console.log('🔧 Please build the backend first by running `build.sh` in the project root directory:')
  console.log('   cd ../..')
  console.log('   ./build.sh')
  console.log('')
  process.exit(1)
}

// Copy the executable
fs.copyFileSync(sourceExecutablePath, destExecutablePath)

// Make executable on Unix systems
if (process.platform !== 'win32') {
  const { execSync } = require('child_process')
  execSync(`chmod +x "${destExecutablePath}"`)
}

// Get file size
const stats = fs.statSync(destExecutablePath)
const fileSizeInMB = (stats.size / (1024 * 1024)).toFixed(2)
console.log(`✅ Copied executable (${fileSizeInMB} MB)`)

// Copy config files
const configDir = path.join(backendDir, 'config')
const sourceConfigDir = path.join(sourceDir, 'dist', 'config')

if (fs.existsSync(sourceConfigDir)) {
  // Create config directory
  if (!fs.existsSync(configDir)) {
    fs.mkdirSync(configDir, { recursive: true })
  }

  // Copy all config files
  const configFiles = fs.readdirSync(sourceConfigDir)
  configFiles.forEach((file) => {
    const src = path.join(sourceConfigDir, file)
    const dest = path.join(configDir, file)
    fs.copyFileSync(src, dest)
  })
  console.log(`✅ Copied ${configFiles.length} config files`)
} else {
  console.log('⚠️  Warning: No config files found')
}

console.log('🎉 Backend ready for packaging')
