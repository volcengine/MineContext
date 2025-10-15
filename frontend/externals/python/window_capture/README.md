# macOS Window Capture

## Steps

1. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
pip3 install pyinstaller
pyinstaller --onedir --name window_capture window_capture.py (optional)
pyinstaller window_capture.spec
```

2. Test run

```bash
./dist/window_capture/window_capture
```

3. Calling in Electron

   Add the following to `build.extraResources` in `package.json`:

```json
{
  "build": {
    "extraResources": [
      {
        "from": "python/window_capture",
        "to": "bin/window_capture"
      }
    ]
  }
}
```
