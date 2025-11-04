#!/bin/bash

# OpenContext Build Script
# Packages the project into a single executable using PyInstaller.

set -e

echo "=== OpenContext Build Script ==="

# 1. Dependency Check
echo "--> Checking for python3..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not found. Please install Python 3."
    exit 1
fi

USE_UV=false
# 2. Check for uv and install dependencies
if command -v uv &> /dev/null; then
    echo "--> Using uv to install dependencies..."
    uv sync
    USE_UV=true
else
    echo "--> uv not found, using pip to install from pyproject.toml..."
    python3 -m pip install -e .
fi

# 3. Install PyInstaller if not present
if [ "$USE_UV" = true ]; then
    # Use uv run to ensure detection within the uv-managed virtual environment
    if ! uv run python -c "import PyInstaller" 2>/dev/null; then
        echo "--> PyInstaller not found (uv env). Installing..."
        uv pip install pyinstaller
    fi
else
    if ! python3 -c "import PyInstaller" 2>/dev/null; then
        echo "--> PyInstaller not found. Installing..."
        python3 -m pip install pyinstaller
    fi
fi

# 4. Clean up previous builds
echo "--> Cleaning up previous build directories..."
rm -rf dist/ build/

# 5. Run PyInstaller build
echo "--> Starting application build with PyInstaller..."
if [ "$USE_UV" = true ]; then
    uv run pyinstaller --clean --noconfirm --log-level INFO opencontext.spec
else
    pyinstaller --clean --noconfirm --log-level INFO opencontext.spec
fi

# 6. Verify build and package
echo "--> Verifying build output..."
EXECUTABLE_NAME="main" # As defined in the original script
if [ -f "dist/$EXECUTABLE_NAME" ] || [ -f "dist/$EXECUTABLE_NAME.exe" ]; then
    echo "✅ Build successful!"

    # Ad-hoc sign for macOS to avoid Gatekeeper issues
    if [[ "$OSTYPE" == "darwin"* ]] && [ -f "dist/$EXECUTABLE_NAME" ]; then
        echo "--> Performing ad-hoc sign for macOS executable..."
        codesign -s - --force --all-architectures --timestamp=none --deep "dist/$EXECUTABLE_NAME" 2>/dev/null || {
            echo "⚠️ Warning: Ad-hoc signing failed. The app might still run, but you may see security warnings."
        }
    fi

    echo "--> Executable is available in the 'dist/' directory."
    ls -la dist/

    # Copy config directory
    if [ -d "config" ]; then
        echo "--> Copying 'config' directory to 'dist/'..."
        cp -r config dist/
        echo "✅ Config directory copied."
    else
        echo "⚠️ Warning: 'config' directory not found."
    fi

    echo
    echo "✅ Build complete!"
    echo
    echo "To run:"
    echo "  cd dist && ./main start"
    echo
    echo "Options: --port 9000 | --host 0.0.0.0 | --config config/config.yaml"
    echo
else
    echo "❌ Build failed. Check the PyInstaller logs above for errors."
    exit 1
fi