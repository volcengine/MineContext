# MAC窗口获取

## 步骤

1. 安装依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
pip3 install pyinstaller
pyinstaller --onedir --name window_inspector window_inspector.py (可选)
pyinstaller window_inspector.spec
```

2. 测试运行

```bash
./dist/window_inspector/window_inspector
```

3. electron中调用

   在 package.json 的 build.extraResources 里加：

```
{
  "build": {
    "extraResources": [
      {
        "from": "python/window_inspector",
        "to": "bin/window_inspector"
      }
    ]
  }
}
```
