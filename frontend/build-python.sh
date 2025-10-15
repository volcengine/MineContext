#!/usr/bin/env bash

# This script builds all necessary Python executables for the application.

set -e # Exit immediately if a command fails.

# Get the directory where this script is located to resolve paths correctly.
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
EXTERNALS_DIR="$SCRIPT_DIR/externals/python"

# --- Reusable Build Function ---
# This function handles the logic for building a single Python executable.
# Arguments:
#   $1: The directory of the Python project to build (e.g., "window_inspector").
build_python_executable() {
    local component_name=$1
    local component_dir="$EXTERNALS_DIR/$component_name"

    echo ""
    echo "--- Building: $component_name ---"

    if [ ! -d "$component_dir" ]; then
        echo "❌ Error: Directory not found at $component_dir"
        return 1
    fi

    echo "📂 Navigating to $component_dir"
    cd "$component_dir"

    # --- Pre-build Check ---
    # Check if the executable already exists to skip unnecessary work.
    local executable_path_dir="dist/$component_name/$component_name"
    local executable_path_file="dist/$component_name"

    if [ -f "$executable_path_dir" ] || [ -f "$executable_path_file" ]; then
        echo "✅ Executable for $component_name already exists. Skipping build."
        return 0 # Successfully skipped
    fi

    echo "🔎 Executable not found for $component_name. Proceeding with build..."

    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv

    echo "🐍 Activating virtual environment..."
    source venv/bin/activate

    if [ -f "requirements.txt" ]; then
        echo "📦 Installing dependencies from requirements.txt..."
        pip3 install -r requirements.txt
    else
        echo "⚠️ Warning: requirements.txt not found in $component_dir."
    fi

    echo "📦 Installing PyInstaller..."
    pip3 install pyinstaller

    if [ -f "$component_name.spec" ]; then
        echo "🛠️ Building executable with PyInstaller ($component_name.spec)..."
        pyinstaller "$component_name.spec"
    else
        echo "❌ Error: $component_name.spec not found. Cannot build."
        deactivate
        return 1
    fi

    # --- Post-build Verification ---
    echo "🔎 Verifying build output..."
    if [ -f "$executable_path_dir" ]; then
        echo "✅ Executable created at $executable_path_dir"
    elif [ -f "$executable_path_file" ]; then
        echo "✅ Executable created at $executable_path_file"
    else
        echo "❌ Error: Build verification failed. Executable not found in 'dist/' directory after build."
        deactivate
        return 1
    fi

    echo "✅ Successfully built $component_name."
    deactivate
}

# --- Build All Components ---
echo "🚀 Starting Python build process..."

build_python_executable "window_inspector"
build_python_executable "window_capture"

echo ""
echo "🎉 All Python executables have been built successfully!"