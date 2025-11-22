# Contributing to Bindu

Thank you for your interest in contributing to Bindu! We're building the Internet of Agents, and your contributions help make that vision a reality. 🌻

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment:

- Be respectful and constructive in all interactions
- Welcome newcomers and help them get started
- Focus on what's best for the community and project
- Accept constructive criticism gracefully
- Show empathy towards other community members

Report any unacceptable behavior to `raahul@getbindu.com`.

## Getting Started

### Prerequisites

- **Python 3.12+** (specifically 3.12.9 recommended)
- **uv** package manager (recommended) or pip
- **Git** for version control
- Basic understanding of async Python and FastAPI
- Familiarity with agent frameworks (Agno, CrewAI, LangChain, etc.) is helpful

### Areas to Contribute

We welcome contributions in several areas:

- **Core Framework**: Improve the Bindu wrapper and protocol implementation
- **Protocol Support**: Enhance A2A, AP2, and X402 compliance
- **Agent Integrations**: Add support for new agent frameworks
- **Documentation**: Improve guides, examples, and API docs
- **Testing**: Increase test coverage (target: 80%+)
- **Examples**: Create demos and use cases
- **Bug Fixes**: Fix reported issues
- **Performance**: Optimize code and reduce latency

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/Bindu.git
cd Bindu

# Add upstream remote
git remote add upstream https://github.com/getbindu/Bindu.git
```

### 2. Set Up Environment

```bash
# Create virtual environment with Python 3.12.9
uv venv --python 3.12.9

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows

# Install dependencies (including dev dependencies)
uv sync --dev
```

### 3. Install Pre-commit Hooks

```bash
# Install pre-commit hooks for code quality
pre-commit install

# Run hooks on all files to verify setup
pre-commit run --all-files
```

### 4. Verify Installation

```bash
# Run tests to ensure everything works
pytest -n auto --cov=bindu --cov-report=term-missing

# Check that coverage is above 70%
coverage report --skip-covered --fail-under=70
```

## How to Contribute

### Finding Issues to Work On

- Check [GitHub Issues](https://github.com/getbindu/Bindu/issues) for open tasks
- Look for issues labeled `good first issue` or `help wanted`
- Join our [Discord](https://discord.gg/3w5zuYUuwt) to discuss ideas
- Attend weekly community meetups (schedule on Discord)

### Before You Start

1. **Check existing issues/PRs** to avoid duplicate work
2. **Comment on the issue** to let others know you're working on it
3. **For major changes**, open an issue first to discuss your approach
4. **Create a branch** from `main` with a descriptive name

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-description
```

## Pull Request Process

### 1. Make Your Changes

- Follow the [coding standards](#coding-standards)
- Write tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic
- Write clear commit messages

### 2. Test Your Changes

```bash
# Run all tests
pytest -n auto

# Run tests with coverage
pytest -n auto --cov=bindu --cov-report=term-missing

# Ensure coverage stays above 70%
coverage report --fail-under=70

# Run pre-commit checks
pre-commit run --all-files
```

### 3. Update Documentation

- Update docstrings for new/modified functions
- Add examples if introducing new features
- Update `README.md` if needed
- Add entry to `CHANGELOG.md` (if applicable)

### 4. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "feat: add support for new agent framework"

# Or for bug fixes
git commit -m "fix: resolve DID resolution timeout issue"
```

**Commit Message Format:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Adding or updating tests
- `refactor:` Code refactoring
- `perf:` Performance improvements
- `chore:` Maintenance tasks

### 5. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub:

1. Go to your fork on GitHub
2. Click "Compare & pull request"
3. Fill out the PR template with:
   - Clear description of changes
   - Related issue numbers (e.g., "Fixes #123")
   - Testing performed
   - Screenshots (if UI changes)
4. Submit the PR

### 6. PR Review Process

- Maintainers will review within 48 hours
- Address any requested changes
- Keep the PR updated with `main` branch
- Once approved, a maintainer will merge

```bash
# Keep your branch updated
git fetch upstream
git rebase upstream/main
git push --force-with-lease origin feature/your-feature-name
```

## Coding Standards

### General Principles

1. **DRY (Don't Repeat Yourself)**: Avoid code duplication
2. **Type Safety**: Use type hints throughout
3. **Best Practices**: Follow Python and async programming best practices
4. **Minimal Code**: Don't write unnecessary code

### Code Style

- **Formatter**: Code is automatically formatted with pre-commit hooks
- **Linting**: Follow PEP 8 guidelines
- **Type Hints**: Use type annotations for all functions


### Async Best Practices

- Use `async`/`await` for I/O operations
- Avoid blocking calls in async functions
- Use `asyncio.gather()` for concurrent operations
- Properly handle async context managers


## Testing Guidelines

### Test Coverage Requirements

- Maintain **minimum 70% coverage** (target: 80%+)
- All new features must include tests
- Bug fixes should include regression tests

### Writing Tests

```python
import pytest
from bindu.core import bindufy

@pytest.mark.asyncio
async def test_agent_initialization():
    """Test that agent initializes correctly."""
    config = {"author": "test@example.com", "name": "test_agent"}
    agent = await bindufy(my_agent, config, handler)

    assert agent.did is not None
    assert agent.name == "test_agent"

def test_did_format():
    """Test DID format generation."""
    did = generate_did("user@example.com", "my_agent", "uuid-123")

    assert did.startswith("did:bindu:")
    assert "my_agent" in did
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_core.py

# Run with coverage
pytest --cov=bindu --cov-report=html

# Run in parallel
pytest -n auto

# Run with verbose output
pytest -v
```


### Documentation Updates

- Update `README.md` for user-facing changes
- Add examples to `examples/` directory
- Update API documentation in `docs/`
- Keep `MAINTAINERS.md` current

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and ideas
- **Discord**: Real-time chat - [Join here](https://discord.gg/3w5zuYUuwt)
- **Weekly Meetups**: Online community meetup every week
  - Schedule announced on Discord and GitHub Discussions
  - Open to all contributors
  - Recordings shared for async participation

### Getting Help

- Check existing documentation and examples
- Search closed issues for similar problems
- Ask on Discord for quick questions
- Open a GitHub Discussion for broader topics
- Attend weekly community meetups

### Recognition

We value all contributions! Contributors are:

- Listed in release notes
- Mentioned in project documentation
- Invited to community events
- Considered for maintainer roles (see [MAINTAINERS.md](../maintainers.md))

## First-Time Contributors

New to open source? We're here to help!

1. Start with issues labeled `good first issue`
2. Read through existing code and tests
3. Ask questions on Discord - no question is too small
4. Pair with a maintainer on your first PR
5. Check out our [examples](../examples/) directory

## License

By contributing to Bindu, you agree that your contributions will be licensed under the [MIT License](../LICENSE).

---

## Questions?

If you have questions about contributing:

- **Discord**: [Join our community](https://discord.gg/3w5zuYUuwt)
- **Email**: raahul@getbindu.com
- **GitHub Discussions**: [Start a discussion](https://github.com/getbindu/Bindu/discussions)

Thank you for contributing to Bindu and helping build the Internet of Agents! 🌻🚀✨
