#!/bin/bash

# Context Lab Build Script
# Packages the project into a single executable using PyInstaller.

set -e

echo "=== Context Lab Build Script ==="

# 1. Dependency Check
echo "--> Checking for python3..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not found. Please install Python 3."
    exit 1
fi

# 2. Install dependencies from requirements.txt
echo "--> Installing dependencies from requirements.txt..."
python3 -m pip install -r requirements.txt

# 3. Install PyInstaller if not present
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "--> PyInstaller not found. Installing..."
    python3 -m pip install pyinstaller
fi

# 4. Clean up previous builds
echo "--> Cleaning up previous build directories..."
rm -rf dist/ build/

# 5. Run PyInstaller build
echo "--> Starting application build with PyInstaller..."
pyinstaller --clean --noconfirm --log-level INFO context-lab.spec

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

    # Create a start script for the packaged application
    echo "--> Creating start script in 'dist/'..."
    cat > dist/start.sh << 'EOF'
#!/bin/bash
# Context Lab Start Script

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the script's directory to ensure paths are correct
cd "$SCRIPT_DIR"

# --- Configuration ---
# Please replace 'your_api_key' with your actual API key before running.
export CONTEXT_API_KEY='your_api_key'

# --- Start Application ---
EXECUTABLE="./main"
if [ -f "$EXECUTABLE" ]; then
    echo "Starting Context Lab..."
    "$EXECUTABLE" start "$@"
elif [ -f "$EXECUTABLE.exe" ]; then
    echo "Starting Context Lab..."
    "$EXECUTABLE.exe" start "$@"
else
    echo "❌ Error: Main executable not found in the current directory."
    exit 1
fi
EOF

    chmod +x dist/start.sh

    echo
    echo "🚀 To run the application:"
    echo "   cd dist/"
    echo "   # IMPORTANT: Edit start.sh to set your CONTEXT_API_KEY"
    echo "   ./start.sh"
    echo
    echo "Alternatively, run the executable directly:"
    echo "   # (Make sure to set the CONTEXT_API_KEY environment variable first)"
    echo "   ./dist/main start"

else
    echo "❌ Build failed. Check the PyInstaller logs above for errors."
    exit 1
fi