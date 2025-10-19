# Configuration Directory

This directory contains configuration files for MineContext.

## Configuration Files

### User Configuration Files (Not Tracked by Git)

These files are specific to each user and are **not tracked** in version control:

- **`config.yaml`** - Your personal configuration file
  - Created from `previous.config.yaml` template
  - Uses environment variables from `.env` file
  - **Add to `.gitignore`** - Already ignored by default

- **`user_setting.yaml`** - User-specific settings
  - Generated at runtime
  - **Add to `.gitignore`** - Already ignored by default

### Template and Example Files (Tracked by Git)

These files are tracked in version control and serve as templates:

- **`previous.config.yaml`** - Configuration template
  - Complete configuration file with all available options
  - Uses environment variable placeholders like `${LLM_BASE_URL}`
  - Copy this to `config.yaml` to get started

- **`config.ollama.example.yaml`** - Ollama-specific example
  - Pre-configured for Ollama local LLM
  - Quick start for Ollama users

### Other Files

- **`prompts_en.yaml`** - English prompts
- **`prompts_zh.yaml`** - Chinese prompts
- **`quick_start_default.md`** - Quick start guide
- **`runtime/`** - Runtime-generated configuration (auto-created, not tracked)

## Quick Setup

### Option 1: Using .env File (Recommended)

1. **Create environment file:**
   ```bash
   # From project root
   cp .env.example .env
   ```

2. **Edit .env with your configuration:**
   ```bash
   # Example for Ollama
   LLM_PROVIDER=ollama
   LLM_MODEL=qwen2.5:14b
   LLM_BASE_URL=http://localhost:11434/v1
   LLM_API_KEY=
   
   EMBEDDING_PROVIDER=ollama
   EMBEDDING_MODEL=nomic-embed-text
   EMBEDDING_BASE_URL=http://localhost:11434/v1
   EMBEDDING_API_KEY=
   ```

3. **Copy config template:**
   ```bash
   cp config/previous.config.yaml config/config.yaml
   ```

4. **Start MineContext:**
   ```bash
   ./start-dev.sh
   ```

The application will automatically load variables from `.env` and substitute them into `config.yaml`.

### Option 2: Using Ollama Example

For quick Ollama setup:

```bash
# From project root
cp config/config.ollama.example.yaml config/config.yaml
```

Then edit `config.yaml` directly with your Ollama configuration.

### Option 3: Using Previous Config as Template

```bash
# From project root
cp config/previous.config.yaml config/config.yaml
```

Then edit `config/config.yaml` with your configuration values.

## Environment Variable Substitution

The `config.yaml` file supports environment variable substitution with the following syntax:

| Syntax | Description | Example |
|--------|-------------|---------|
| `${VAR}` | Required variable | `${LLM_MODEL}` |
| `${VAR:}` | Optional, empty if not set | `${LLM_API_KEY:}` |
| `${VAR:default}` | Optional, use default if not set | `${LLM_PROVIDER:ollama}` |
| `${VAR:${OTHER}}` | Optional, fallback to another variable | `${EMBEDDING_BASE_URL:${LLM_BASE_URL}}` |

### Example Configuration

**config.yaml:**
```yaml
vlm_model:
  base_url: "${LLM_BASE_URL}"
  api_key: "${LLM_API_KEY:}"
  model: "${LLM_MODEL}"
  provider: "${LLM_PROVIDER:}"

embedding_model:
  base_url: "${EMBEDDING_BASE_URL:${LLM_BASE_URL}}"  # Falls back to LLM_BASE_URL
  api_key: "${EMBEDDING_API_KEY:${LLM_API_KEY}}"    # Falls back to LLM_API_KEY
  model: "${EMBEDDING_MODEL}"
  provider: "${EMBEDDING_PROVIDER:${LLM_PROVIDER}}"  # Falls back to LLM_PROVIDER
```

**.env:**
```bash
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:14b
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=

EMBEDDING_MODEL=nomic-embed-text
# Note: EMBEDDING_PROVIDER, EMBEDDING_BASE_URL, and EMBEDDING_API_KEY are not set
# They will automatically fall back to the LLM_* values
```

**Result (at runtime):**
```yaml
vlm_model:
  base_url: "http://localhost:11434/v1"
  api_key: ""
  model: "qwen2.5:14b"
  provider: "ollama"

embedding_model:
  base_url: "http://localhost:11434/v1"      # From LLM_BASE_URL
  api_key: ""                                # From LLM_API_KEY
  model: "nomic-embed-text"
  provider: "ollama"                         # From LLM_PROVIDER
```

## Best Practices

### Security

1. **Never commit `config.yaml` or `.env`** to version control
   - Both are already in `.gitignore`
   - They may contain API keys and sensitive information

2. **Use `.env` file for sensitive data**
   - API keys should be in `.env`, not `config.yaml`
   - Environment variables are loaded before config parsing

3. **Share templates, not credentials**
   - Commit: `.env.example`, `previous.config.yaml`
   - Don't commit: `.env`, `config.yaml`

### Configuration Management

1. **Keep environment-specific configs separate**
   ```bash
   .env.development
   .env.production
   .env.testing
   ```

2. **Document your changes**
   - If you add new config options to `previous.config.yaml`, document them
   - Update `.env.example` with corresponding environment variables

3. **Test configuration changes**
   - Validate syntax with: `python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"`
   - Check environment variable loading: `./start-dev.sh` will show loaded vars

## Troubleshooting

### Issue: "Configuration file not found"

**Solution:**
```bash
# Copy the template
cp config/previous.config.yaml config/config.yaml
```

### Issue: "Environment variable not set"

**Solution:**
```bash
# Check if .env exists
ls -la .env

# If not, create it
cp .env.example .env

# Edit .env with your values
nano .env  # or vim, code, etc.
```

### Issue: "API key is empty"

For local providers like Ollama, this is expected and correct.

For cloud providers (OpenAI, Doubao):
1. Check `.env` file has `LLM_API_KEY=your-actual-key`
2. No spaces around `=`: ✅ `KEY=value` ❌ `KEY = value`
3. Restart the application: `./start-dev.sh`

### Issue: "Changes to .env not reflected"

**Solution:**
Environment variables are loaded at startup. Restart the application:
```bash
# Stop with Ctrl+C
# Start again
./start-dev.sh
```

## Related Documentation

- [Environment Variables Guide](../docs/ENV_CONFIGURATION.md) - Detailed .env usage
- [LLM Configuration Guide](../docs/LLM_CONFIGURATION_GUIDE.md) - LLM setup
- [Main README](../README.md) - Project overview

## Support

For issues or questions:
- GitHub Issues: https://github.com/volcengine/MineContext/issues
- Documentation: https://github.com/volcengine/MineContext
