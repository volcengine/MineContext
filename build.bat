@echo off
REM OpenContext Build Script for Windows
REM Packages the project into a single executable using PyInstaller.

setlocal enabledelayedexpansion

echo === OpenContext Build Script ===
echo.

REM 1. Dependency Check
echo --^> Checking for python...
where py >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo Error: python is not found. Please install Python 3.
        exit /b 1
    )
    set PYTHON_CMD=python
)
%PYTHON_CMD% --version

set USE_UV=false

REM 2. Check for uv and install dependencies
where uv >nul 2>&1
if %errorlevel% equ 0 (
    echo --^> Using uv to install dependencies...
    uv sync
    if errorlevel 1 (
        echo Error: uv sync failed.
        exit /b 1
    )
    set USE_UV=true
) else (
    echo --^> uv not found, using pip to install from pyproject.toml...
    %PYTHON_CMD% -m pip install -e .
    if errorlevel 1 (
        echo Error: pip install failed.
        exit /b 1
    )
)

REM 3. Install PyInstaller if not present
if "!USE_UV!"=="true" (
    REM Use uv run to ensure detection within the uv-managed virtual environment
    uv run python -c "import PyInstaller" >nul 2>&1
    if errorlevel 1 (
        echo --^> PyInstaller not found ^(uv env^). Installing...
        uv pip install pyinstaller
        if errorlevel 1 (
            echo Error: Failed to install PyInstaller with uv.
            exit /b 1
        )
    )
) else (
    %PYTHON_CMD% -c "import PyInstaller" >nul 2>&1
    if errorlevel 1 (
        echo --^> PyInstaller not found. Installing...
        %PYTHON_CMD% -m pip install pyinstaller
        if errorlevel 1 (
            echo Error: Failed to install PyInstaller with pip.
            exit /b 1
        )
    )
)

REM 4. Clean up previous builds
echo --^> Cleaning up previous build directories...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

REM 5. Run PyInstaller build
echo --^> Starting application build with PyInstaller...
if "!USE_UV!"=="true" (
    uv run pyinstaller --clean --noconfirm --log-level INFO opencontext.spec
) else (
    pyinstaller --clean --noconfirm --log-level INFO opencontext.spec
)

if errorlevel 1 (
    echo Error: PyInstaller build failed.
    exit /b 1
)

REM 6. Verify build and package
echo --^> Verifying build output...
set EXECUTABLE_NAME=main
if exist "dist\%EXECUTABLE_NAME%.exe" (
    echo Build successful!
    echo.

    echo --^> Executable is available in the 'dist\' directory.
    dir dist
    echo.

    REM Copy config directory
    if exist "config" (
        echo --^> Copying 'config' directory to 'dist\'...
        xcopy /E /I /Y config dist\config >nul
        echo Config directory copied.
        echo.
    ) else (
        echo Warning: 'config' directory not found.
        echo.
    )

    echo Build complete!
    echo.
    echo To run:
    echo   cd dist ^&^& main.exe start
    echo.
    echo Options: --port 9000 ^| --host 0.0.0.0 ^| --config config\config.yaml
    echo.
) else (
    echo Error: Build failed. Check the PyInstaller logs above for errors.
    exit /b 1
)

endlocal
