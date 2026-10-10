# Fix: Embedding Provider Inheritance

## Bug Summary

When configuring a separate embedding server (`embeddingBaseUrl`) alongside a Doubao/Ark main LLM, all embedding requests failed because the Ark SDK was used to call an OpenAI-compatible endpoint.

## Root Cause

The provider fallback logic was `emb_provider = cfg.embeddingModelPlatform or cfg.modelPlatform`. When no explicit embedding provider was set, it inherited the main LLM provider (Doubao). The Ark SDK was then used against an OpenAI-compatible URL, causing authentication and API-shape errors.

The same bug existed in both `update_model_settings` and `validate_llm_config`.

## Bug Flow

```mermaid
flowchart TD
    A[User sets embeddingBaseUrl to OpenAI-compatible server] --> B[embeddingModelPlatform = not set]
    B --> C[Fallback: emb_provider = modelPlatform]
    C --> D[modelPlatform = doubao]
    D --> E[LLMClient instantiates Ark SDK for embeddings]
    E --> F[Ark SDK calls Ark-specific API endpoint]
    F --> G[BUG: OpenAI server rejects Ark auth format]
    G --> H[All embedding requests fail]
```

## Fix Flow

```mermaid
flowchart TD
    A[User sets embeddingBaseUrl] --> B{embeddingBaseUrl present?}
    B -- Yes --> C[Fallback = LLMProvider.OPENAI]
    B -- No --> D[Fallback = cfg.modelPlatform\npreserves Doubao-only setups]
    C --> E[LLMClient instantiates OpenAI SDK]
    E --> F[OpenAI SDK calls embeddingBaseUrl correctly]
    F --> G[Embeddings succeed]
    D --> H[Ark SDK used for Doubao-only setup\nUnchanged behaviour]
```

## Files Changed

| File | Change |
|------|--------|
| `opencontext/server/routes/settings.py` | Fixed provider fallback in `update_model_settings` and `validate_llm_config` |

## PR Description

**Title:** `fix(settings): preserve embedding provider when a separate embedding server is configured`

When a user configures a separate embedding server (`embeddingBaseUrl`) alongside a Doubao/Ark main LLM, the application overwrites the embedding provider with the main LLM provider. The Ark SDK is then used to call an OpenAI-compatible endpoint, and every embedding request fails.

When `embeddingBaseUrl` is set, the fix falls back to `LLMProvider.OPENAI` instead of inheriting the main model platform. Setups without a separate embedding URL are unchanged.

**Fixes #355, #346, #351**
