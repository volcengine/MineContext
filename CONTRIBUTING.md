# Contributing to MineContext

Thank you for your interest in contributing to MineContext! We welcome contributions from the community.

## Getting Started

### Development Setup

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/MineContext.git
   cd MineContext
   ```
2. **Set up your environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Configure and run**

   ```bash
   # Start the server
   python -m opencontext.cli start
   ```

## How to Contribute

### Reporting Issues

Found a bug or have a feature request? [Create an issue](https://github.com/volcengine/MineContext/issues) with:

- Clear description of the problem or feature
- Steps to reproduce (for bugs)
- Your environment (OS, Python version, MineContext version)

### Branch Naming Convention

Use descriptive branch names with appropriate prefixes:

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feature/` or `feat/` | New features | `feature/add-notion-integration` |
| `fix/` | Bug fixes | `fix/screenshot-capture-error` |
| `hotfix/` | Critical production fixes | `hotfix/memory-leak` |
| `docs/` | Documentation only | `docs/update-api-guide` |
| `refactor/` | Code refactoring | `refactor/simplify-storage-layer` |
| `test/` | Adding or updating tests | `test/add-processor-tests` |
| `chore/` | Maintenance tasks | `chore/update-dependencies` |

### Submitting Code

1. **Create a branch**

   Follow the branch naming convention above:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**

   - Follow [PEP 8](https://pep8.org/) style guidelines
   - Add tests for new features
   - Update documentation if needed

3. **Commit with clear messages**

   ```bash
   git commit -m "feat: add your feature description"
   # or
   git commit -m "fix: fix your bug description"
   ```

4. **Push and create a Pull Request**

   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Keep functions focused and well-documented
- Maximum line length: 100 characters

## Priority Areas

We especially welcome contributions in these areas:

- **P0-P1**: Link upload, file processing (documents, images, audio, video)
- **P2-P3**: MCP/API integrations (Notion, Obsidian, Figma), meeting recording
- **P4-P5**: Mobile screenshot monitoring, smart device sync

See the [Context Sources](README.md#-context-source) section for more details.

## Community

- **Issues**: [GitHub Issues](https://github.com/volcengine/MineContext/issues)
- **WeChat/Lark**: [Join our group](https://bytedance.larkoffice.com/wiki/Hg6VwrxnTiXtWUkgHexcFTqrnpg)
- **Discord**: [Join here](https://discord.gg/tGj7RQ3nUR)

## License

By contributing, you agree that your contributions will be licensed under the [Apache 2.0 License](LICENSE).
