#!/usr/bin/env bash
set -e

# 确定脚本所在的目录
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
CONTEXT_LAB_DIR="$SCRIPT_DIR/.."
FRONTEND_DIR="$SCRIPT_DIR"

# --- 函数定义 ---

# 显示帮助信息
show_help() {
    echo "用法: ./start-dev.sh [命令]"
    echo ""
    echo "一个用于设置和运行开发环境的脚本。"
    echo ""
    echo "命令:"
    echo "  (无命令)      执行完整的后端和前端构建，并启动开发服务器。"
    echo "  backend         仅构建和准备 MineContext 后端。"
    echo "  frontend        仅安装前端依赖并准备前端环境 (包括 Python 部分)。"
    echo "  frontend-py     仅构建前端所需的 Python 可执行文件。"
    echo "  web serve       启动 MineContext 的 Web 服务器。"
    echo "  -h, --help      显示此帮助信息。"
}

# 构建后端 (MineContext)
build_backend() {
    echo "--- ⚙️  构建后端 (MineContext) ---"

    # 项目根目录是 SCRIPT_DIR 的上一级
    PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

    echo "📂 切换到项目根目录: $PROJECT_ROOT"
    cd "$PROJECT_ROOT"

    # 检测并安装 UV
    if ! command -v uv &> /dev/null; then
        echo "🔎 UV 未安装，正在从 astral.sh 安装..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        echo "✅ UV 安装完成。"
    else
        echo "✅ UV 已安装。"
    fi

    echo "🐍 使用 uv 同步 Python 环境和依赖..."
    uv sync

    echo "🔌 激活 Python 虚拟环境..."
    source .venv/bin/activate

    echo "🛠️  执行 MineContext 构建脚本..."
    ./build.sh

    echo "✅ 后端构建完成。"
}

# 构建前端的 Python 组件
build_python_component() {
    local component_name=$1
    local component_dir="$FRONTEND_DIR/externals/python/$component_name"
    local dist_path_one_folder="$component_dir/dist/$component_name/$component_name"
    local dist_path_one_file="$component_dir/dist/$component_name"

    echo "--- 🐍 构建 Python 组件: $component_name ---"

    # 检查可执行文件是否已存在
    if [ -f "$dist_path_one_folder" ] || [ -f "$dist_path_one_file" ]; then
        echo "✅ 组件 '$component_name' 的可执行文件已存在，跳过构建。"
        return
    fi
    
    if [ ! -d "$component_dir" ]; then
        echo "❌ 错误: 组件 '$component_name' 的目录未找到: '$component_dir'"
        exit 1
    fi

    echo "📂 切换到目录: $component_dir"
    cd "$component_dir"

    echo "🐍 创建 Python 虚拟环境..."
    python3 -m venv venv

    echo "激活虚拟环境..."
    source venv/bin/activate

    if [ -f "requirements.txt" ]; then
        echo "📦 从 requirements.txt 安装依赖..."
        pip3 install -r requirements.txt
    else
        echo "⚠️ 未找到 $component_name 的 requirements.txt 文件。"
    fi
    
    echo "📦 安装 PyInstaller..."
    pip3 install pyinstaller

    if [ -f "$component_name.spec" ]; then
        echo "🛠️ 使用 $component_name.spec 通过 PyInstaller 构建..."
        pyinstaller "$component_name.spec"
    else
        echo "❌ 错误: 在 $component_dir 中未找到 $component_name.spec"
        exit 1
    fi
    
    echo "✅ 组件 '$component_name' 构建成功。"
    
    # 停用虚拟环境
    deactivate
}

# 设置前端的 Python 环境
setup_frontend_python() {
    echo "--- 🐍  设置前端 Python 可执行文件 ---"
    build_python_component "window_capture"
    build_python_component "window_inspector"
    echo "✅ 前端 Python 可执行文件设置完成。"
}

# 定义清理函数
cleanup() {
    echo ""
    echo "🔄 清理临时文件..."
    
    # 删除本地 .python-version 文件
    if [ -f .python-version ]; then
        rm .python-version
        echo "✅ 已删除 .python-version 文件"
    fi
    
    echo "✅ 清理完成！"
    echo "ℹ️  环境变量会在脚本结束后自动清除"
}
trap cleanup EXIT
# 设置前端
setup_frontend() {
    echo "--- ⚛️  设置前端 ---"
    
    # 首先构建 Python 部分
    setup_frontend_python
    
    echo "📂 切换回 frontend 目录: $FRONTEND_DIR"
    cd "$FRONTEND_DIR"
    rm -rf node_modules
    # 检查 nvm 是否已加载
    if ! command -v nvm &> /dev/null; then
        echo "nvm 命令未找到，尝试从标准位置加载..."
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
        [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
    fi

    if command -v nvm &> /dev/null; then
        echo "📦 安装并使用稳定的 Node.js 版本..."
        nvm install stable
        nvm use stable
    else
        echo "⚠️ nvm 未安装或无法加载。请确保 nvm 已正确安装。跳过 nvm 步骤。"
    fi

        # 检测并安装 pyenv
    if ! command -v pyenv &> /dev/null; then
        echo "🔎 pyenv 未安装。正在尝试使用 Homebrew 安装..."
        if ! command -v brew &> /dev/null; then
            echo "❌ Homebrew 未安装。请先安装 Homebrew，然后再运行此脚本。"
            exit 1
        fi
        brew install pyenv
        echo "✅ pyenv 安装完成。"
    else
        echo "✅ pyenv 已安装。"
    fi

    # 使用 pyenv 安装并设置 Python 3.11.9
    PYTHON_VERSION="3.11.9"
    if ! pyenv versions --bare | grep -q "^$PYTHON_VERSION$"; then
        echo "🐍 正在使用 pyenv 安装 Python $PYTHON_VERSION..."
        pyenv install $PYTHON_VERSION
    else
        echo "✅ Python $PYTHON_VERSION 已通过 pyenv 安装。"
    fi
    echo "🔧 设置本地 Python 版本为 $PYTHON_VERSION..."
    pyenv local $PYTHON_VERSION

    # ===== 新增部分 =====
    # 获取 pyenv 管理的 Python 路径
    PYTHON_PATH=$(pyenv which python)
    echo "🔍 当前 Python 路径: $PYTHON_PATH"
    # 检测并安装 pnpm
    if ! command -v pnpm &> /dev/null; then
        echo "🔎 pnpm 未安装。正在使用 npm 进行全局安装..."
        npm install -g pnpm
        echo "✅ pnpm 安装完成。"
    else
        echo "✅ pnpm 已安装。"
    fi
    # 验证 Python 版本
    CURRENT_PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    echo "✅ 当前 Python 版本: $CURRENT_PYTHON_VERSION"

    # 设置环境变量（仅在脚本执行期间有效）
    export PYTHON="$PYTHON_PATH"
    export npm_config_python="$PYTHON_PATH"
    echo "⚙️  已设置临时环境变量（脚本结束后自动清除）"
    
    echo "📦 安装 pnpm 依赖..."
    pnpm install

    echo "🚚 复制后端文件..."
    pnpm run copy-backend

    echo "🛠️ 构建外部依赖 (JS)..."
    pnpm run build:externals
    
    echo "✅ 前端设置完成。"

    
}



# 启动 MineContext web 服务器
start_web_serve() {
    echo "--- 🌐 启动 MineContext Web 服务器 ---"
    echo "📂 切换到 MineContext 目录: $CONTEXT_LAB_DIR"
    cd "$CONTEXT_LAB_DIR"

    echo "激活虚拟环境..."
    source venv/bin/activate
    
    echo "🚀 启动服务器..."
    python3 -m opencontext.cli start
}


# --- 主逻辑 ---

# 检查帮助标志
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

echo "🚀 开始开发环境启动脚本..."

# 如果没有参数，执行默认的完整流程
if [ -z "$1" ]; then
    build_backend
    setup_frontend
    
    echo "--- 🚀 启动开发服务器 ---"
    cd "$FRONTEND_DIR"
    pnpm run dev
    echo "✅ 开发环境已成功启动！"

# 根据参数执行特定任务
else
    case "$1" in
        backend)
            build_backend
            ;;
        frontend)
            setup_frontend
            ;;
        frontend-py)
            setup_frontend_python
            ;;
        web)
            if [ "$2" == "serve" ]; then
                start_web_serve
            else
                echo "错误: 'web' 命令需要 'serve' 作为第二个参数。" >&2
                exit 1
            fi
            ;;
        *)
            echo "错误: 未知命令 '$1'" >&2
            echo ""
            show_help
            exit 1
            ;;
    esac
    echo "✅ 任务 '$*' 已完成。"
fi



