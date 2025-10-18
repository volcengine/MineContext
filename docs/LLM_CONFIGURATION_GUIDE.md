# LLM Configuration Guide

This guide explains how to configure custom VLM (Vision-Language Model) and Embedding models in MineContext, including support for local providers that don't require API keys.

## Table of Contents

- [Overview](#overview)
- [Supported Providers](#supported-providers)
- [Configuration Structure](#configuration-structure)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Overview

MineContext supports flexible LLM configuration, allowing you to:

✅ Use cloud-based providers (OpenAI, Doubao, etc.)  
✅ Use local providers (Ollama, LocalAI, LlamaCPP)  
✅ Mix and match providers for VLM and Embedding  
✅ Use custom OpenAI-compatible endpoints  

### Key Features

1. **Optional API Keys**: Local providers like Ollama, LocalAI, and LlamaCPP don't require API keys
2. **Automatic Validation**: Configuration is validated before being saved
3. **Graceful Rollback**: If reinitialization fails, the system reverts to the previous working configuration
4. **Flexible Provider Support**: Any OpenAI-compatible API can be used

## Supported Providers

### Providers with Optional API Keys

The following providers **do NOT require** API keys:

- **Ollama** (`provider: "ollama"`)
- **LocalAI** (`provider: "localai"`)
- **LlamaCPP** (`provider: "llamacpp"`)

### Providers Requiring API Keys

- **OpenAI** (`provider: "openai"` or `provider: ""`)
- **Doubao** (`provider: "doubao"`)
- **Custom** (`provider: "custom"`) - Depends on your endpoint

## Configuration Structure

### VLM Model Configuration

```yaml
vlm_model:
  base_url: "http://localhost:11434/v1"  # API endpoint
  api_key: ""                             # Empty for local providers
  model: "qwen2.5:14b"                    # Model ID
  provider: "ollama"                      # Provider type
  temperature: 0.7                        # Optional: sampling temperature
```

### Embedding Model Configuration

```yaml
embedding_model:
  base_url: "http://localhost:11434/v1"  # API endpoint
  api_key: ""                             # Empty for local providers
  model: "nomic-embed-text"               # Model ID
  provider: "ollama"                      # Provider type
  output_dim: 768                         # Optional: output dimensions
```

## Examples

### Example 1: Ollama for Both VLM and Embedding

```yaml
vlm_model:
  base_url: "http://localhost:11434/v1"
  api_key: ""
  model: "qwen2.5:14b"
  provider: "ollama"
  temperature: 0.7

embedding_model:
  base_url: "http://localhost:11434/v1"
  api_key: ""
  model: "nomic-embed-text"
  provider: "ollama"
  output_dim: 768
```

**Quick Start with Ollama:**

```bash
# 1. Install Ollama (https://ollama.ai)
curl -fsSL https://ollama.ai/install.sh | sh

# 2. Pull the models
ollama pull qwen2.5:14b
ollama pull nomic-embed-text

# 3. Copy the example config
cp config/config.ollama.example.yaml config/config.yaml

# 4. Start MineContext
python -m opencontext.cli start
```

### Example 2: OpenAI for VLM, Ollama for Embedding

```yaml
vlm_model:
  base_url: "https://api.openai.com/v1"
  api_key: "${LLM_API_KEY}"  # From environment variable
  model: "gpt-4o"
  provider: "openai"
  temperature: 0.7

embedding_model:
  base_url: "http://localhost:11434/v1"
  api_key: ""
  model: "nomic-embed-text"
  provider: "ollama"
  output_dim: 768
```

### Example 3: Custom OpenAI-Compatible Endpoint

```yaml
vlm_model:
  base_url: "https://my-custom-endpoint.com/v1"
  api_key: "your-api-key-here"
  model: "custom-model-name"
  provider: "custom"
  temperature: 0.7

embedding_model:
  base_url: "https://my-custom-endpoint.com/v1"
  api_key: "your-api-key-here"
  model: "custom-embedding-model"
  provider: "custom"
  output_dim: 1536
```

### Example 4: LocalAI

```yaml
vlm_model:
  base_url: "http://localhost:8080/v1"
  api_key: ""  # LocalAI typically doesn't require auth
  model: "gpt-3.5-turbo"  # Your LocalAI model name
  provider: "localai"
  temperature: 0.7

embedding_model:
  base_url: "http://localhost:8080/v1"
  api_key: ""
  model: "all-MiniLM-L6-v2"
  provider: "localai"
  output_dim: 384
```

### Example 5: Environment Variables

Use environment variables for sensitive data:

```yaml
vlm_model:
  base_url: "${LLM_BASE_URL}"
  api_key: "${LLM_API_KEY}"
  model: "${LLM_MODEL}"
  provider: "${LLM_PROVIDER:openai}"
  temperature: 0.7

embedding_model:
  base_url: "${EMBEDDING_BASE_URL}"
  api_key: "${EMBEDDING_API_KEY}"
  model: "${EMBEDDING_MODEL}"
  provider: "${EMBEDDING_PROVIDER:openai}"
  output_dim: 2048
```

Then set environment variables:

```bash
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4o"
export LLM_PROVIDER="openai"

export EMBEDDING_BASE_URL="https://api.openai.com/v1"
export EMBEDDING_API_KEY="sk-..."
export EMBEDDING_MODEL="text-embedding-3-large"
export EMBEDDING_PROVIDER="openai"
```

## Configuration via Web UI

You can also configure models through the web interface:

1. Open http://localhost:8000 in your browser
2. Navigate to **Settings** → **Model Configuration**
3. Fill in the following fields:
   - **Provider**: Select the provider type (ollama, openai, etc.)
   - **Base URL**: API endpoint
   - **API Key**: Leave empty for local providers
   - **Model ID**: Model identifier
4. Click **Validate** to test the configuration
5. Click **Save** to apply changes

The system will automatically validate the configuration and reinitialize the clients.

## Troubleshooting

### Issue: "API key must be provided"

**Cause:** You're using a cloud provider but didn't provide an API key.

**Solution:** Either:
- Set the `api_key` field in your configuration
- Change `provider` to a local provider like "ollama" if using a local endpoint

### Issue: "VLM validation failed"

**Cause:** The configuration is invalid or the endpoint is unreachable.

**Solution:**
1. Check that the `base_url` is correct and the service is running
2. Verify the `model` name matches an available model
3. For local providers, ensure the service is started:
   ```bash
   # For Ollama
   ollama serve
   
   # For LocalAI
   docker run -p 8080:8080 localai/localai
   ```

### Issue: "Failed to reinitialize clients"

**Cause:** The new configuration failed validation, and the system rolled back.

**Solution:**
1. Check the logs for detailed error messages
2. Verify your configuration against the examples above
3. Test the endpoint manually:
   ```bash
   # For Ollama
   curl http://localhost:11434/v1/models
   
   # For OpenAI-compatible
   curl https://your-endpoint/v1/models \
     -H "Authorization: Bearer your-api-key"
   ```

### Issue: Empty API key for cloud providers

**Cause:** Environment variable is not set or configuration uses `""` for a cloud provider.

**Solution:**
- For **local providers**: Set `provider: "ollama"` (or `"localai"`, `"llamacpp"`)
- For **cloud providers**: Set a valid API key or environment variable

### Best Practices

1. **Use environment variables** for sensitive data (API keys)
2. **Test with validation endpoint** before saving configuration
3. **Check logs** for detailed error messages
4. **Start with simple configuration** and add complexity gradually
5. **Use local providers** for development to avoid API costs

## Architecture Notes

### Validation and Rollback Mechanism

When you update model settings:

1. **Validation**: Both VLM and Embedding configurations are validated by making test API calls
2. **Save**: Configuration is saved to `user_setting.yaml`
3. **Reinitialization**: Clients are reinitialized with the new configuration
4. **Rollback**: If reinitialization fails, the previous working client is restored

This ensures the system remains operational even if you accidentally provide an invalid configuration.

### Provider Detection

The system automatically detects whether API keys are required based on the `provider` field:

```python
# In llm_client.py
@classmethod
def is_api_key_optional(cls, provider: str) -> bool:
    optional_providers = ["ollama", "localai", "llamacpp"]
    return provider.lower() in optional_providers
```

## API Reference

### Configuration Fields

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `base_url` | Yes | API endpoint URL | `http://localhost:11434/v1` |
| `api_key` | Conditional | Authentication key (optional for local providers) | `sk-...` or `""` |
| `model` | Yes | Model identifier | `qwen2.5:14b` |
| `provider` | Yes | Provider type | `ollama`, `openai`, `custom` |
| `temperature` | No (VLM only) | Sampling temperature | `0.7` |
| `output_dim` | No (Embedding only) | Output dimensions | `768` |

### Supported Provider Values

- `ollama` - Ollama (no API key required)
- `localai` - LocalAI (no API key required)
- `llamacpp` - LlamaCPP (no API key required)
- `openai` - OpenAI (requires API key)
- `doubao` - Doubao (requires API key)
- `custom` - Custom provider (may require API key)

## Contributing

If you're using a provider not listed here, please:

1. Test if it works with `provider: "custom"`
2. Submit a PR to add it to the `LLMProvider` enum if needed
3. Update this documentation with your example

## Support

For issues or questions:
- GitHub Issues: https://github.com/volcengine/MineContext/issues
- Documentation: https://github.com/volcengine/MineContext
