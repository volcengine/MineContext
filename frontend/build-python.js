#!/usr/bin/env node

// Cross-platform Python build script
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

console.log('🚀 Starting Python build process...');

// Get the directory where this script is located
const scriptDir = __dirname;
const externalsDir = path.join(scriptDir, 'externals', 'python');

// Function to run shell commands
function runCommand(command, options = {}) {
  try {
    console.log(`Running: ${command}`);
    execSync(command, {
      stdio: 'inherit',
      cwd: options.cwd || scriptDir,
      shell: true,
      ...options
    });
  } catch (error) {
    console.error(`❌ Command failed: ${command}`);
    throw error;
  }
}

// Function to check if executable exists
function executableExists(componentName) {
  const executablePathDir = path.join(externalsDir, componentName, 'dist', componentName, componentName);
  const executablePathFile = path.join(externalsDir, componentName, 'dist', componentName);

  return fs.existsSync(executablePathDir) || fs.existsSync(executablePathFile);
}

// Function to build Python executable
function buildPythonExecutable(componentName) {
  console.log(`\n--- Building: ${componentName} ---`);

  const componentDir = path.join(externalsDir, componentName);

  if (!fs.existsSync(componentDir)) {
    console.error(`❌ Error: Directory not found at ${componentDir}`);
    return false;
  }

  console.log(`📂 Navigating to ${componentDir}`);

  // Check if executable already exists
  if (executableExists(componentName)) {
    console.log(`✅ Executable for ${componentName} already exists. Skipping build.`);
    return true;
  }

  console.log(`🔎 Executable not found for ${componentName}. Proceeding with build...`);

  try {
    // Create virtual environment
    console.log('🐍 Creating Python virtual environment...');
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    runCommand(`${pythonCmd} -m venv venv`, { cwd: componentDir });

    // Activate virtual environment and install dependencies
    console.log('🐍 Activating virtual environment...');
    const pipCmd = process.platform === 'win32' ? 'venv\\Scripts\\pip' : 'venv/bin/pip3';

    // Install requirements if exists
    const requirementsPath = path.join(componentDir, 'requirements.txt');
    if (fs.existsSync(requirementsPath)) {
      console.log('📦 Installing dependencies from requirements.txt...');
      runCommand(`${pipCmd} install -r requirements.txt`, { cwd: componentDir });
    } else {
      console.log(`⚠️ Warning: requirements.txt not found in ${componentDir}.`);
    }

    // Install PyInstaller
    console.log('📦 Installing PyInstaller...');
    runCommand(`${pipCmd} install pyinstaller`, { cwd: componentDir });

    // Build with PyInstaller
    const specPath = path.join(componentDir, `${componentName}.spec`);
    if (fs.existsSync(specPath)) {
      console.log(`🛠️ Building executable with PyInstaller (${componentName}.spec)...`);
      const pyinstallerCmd = process.platform === 'win32' ? 'venv\\Scripts\\pyinstaller' : 'venv/bin/pyinstaller';
      runCommand(`${pyinstallerCmd} ${componentName}.spec`, { cwd: componentDir });
    } else {
      console.error(`❌ Error: ${componentName}.spec not found. Cannot build.`);
      return false;
    }

    // Verify build output
    console.log('🔎 Verifying build output...');
    if (executableExists(componentName)) {
      console.log(`✅ Successfully built ${componentName}.`);
      return true;
    } else {
      console.error(`❌ Error: Build verification failed. Executable not found in 'dist/' directory after build.`);
      return false;
    }

  } catch (error) {
    console.error(`❌ Error building ${componentName}:`, error.message);
    return false;
  }
}

// Build all components
const components = ['window_inspector', 'window_capture'];
let allSuccess = true;

// Skip macOS-specific tools on Windows
if (process.platform === 'win32') {
  console.log('⚠️  Skipping macOS-specific Python tools on Windows platform');
  console.log('   These tools (window_inspector, window_capture) are designed for macOS only');
  console.log('   and use the Quartz framework which is not available on Windows.');
  console.log('✅ Build process completed (skipped macOS tools)');
  process.exit(0);
}

for (const component of components) {
  if (!buildPythonExecutable(component)) {
    allSuccess = false;
  }
}

if (allSuccess) {
  console.log('\n🎉 All Python executables have been built successfully!');
  process.exit(0);
} else {
  console.log('\n❌ Some Python executables failed to build.');
  process.exit(1);
}
