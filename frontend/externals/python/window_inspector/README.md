# macOS Window Inspector

## Steps

1. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
pip3 install pyinstaller
pyinstaller --onedir --name window_inspector window_inspector.py (optional)
pyinstaller window_inspector.spec
```

2. Test run

```bash
./dist/window_inspector/window_inspector
```

3. Calling in Electron

   Add the following to `build.extraResources` in `package.json`:

```json
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
