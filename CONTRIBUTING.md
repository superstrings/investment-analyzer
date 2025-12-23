# Contributing to Investment Analyzer

Thank you for your interest in contributing to Investment Analyzer! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- A clear, descriptive title
- Detailed steps to reproduce the issue
- Expected behavior vs actual behavior
- Your environment (Python version, OS, database version)
- Error messages and stack traces if applicable

### Suggesting Features

Feature requests are welcome! Please:

- Check if the feature has already been suggested
- Provide a clear description of the feature
- Explain the use case and benefits
- Consider implementation complexity

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Follow the coding style** - we use Black, isort, and flake8
3. **Write tests** - ensure new features have test coverage
4. **Update documentation** - keep docs in sync with code changes
5. **Run the test suite** - all tests must pass

## Development Setup

### Prerequisites

- Python 3.12.x (managed via asdf)
- PostgreSQL 17
- Futu OpenD (for live data, optional for development)

### Setup Steps

```bash
# Clone the repository
git clone https://github.com/your-username/investment-analyzer.git
cd investment-analyzer

# Set Python version (using asdf)
asdf install python 3.12.7
asdf local python 3.12.7

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python scripts/init_db.py create-db
python scripts/init_db.py init

# Run tests
python -m pytest tests/ -v
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=.

# Run specific test file
python -m pytest tests/test_config.py -v
```

### Code Style

We use the following tools to maintain code quality:

```bash
# Format code with Black
python -m black .

# Sort imports with isort
python -m isort .

# Lint with flake8
python -m flake8 .
```

Before submitting a PR, ensure all checks pass:

```bash
python -m black --check .
python -m isort --check .
python -m flake8 .
python -m pytest tests/ -v
```

## Project Structure

```
investment-analyzer/
├── analysis/          # Technical analysis and indicators
├── backtest/          # Backtesting framework
├── charts/            # Chart generation
├── cli/               # CLI utilities
├── config/            # Configuration management
├── db/                # Database models and migrations
├── fetchers/          # Data fetchers (Futu, akshare)
├── reports/           # Report generation
├── scripts/           # Utility scripts
├── services/          # Business logic services
├── skills/            # Claude Code skills
└── tests/             # Test suite
```

## Commit Messages

Use clear, descriptive commit messages:

- `feat: add new feature` - New features
- `fix: resolve bug` - Bug fixes
- `docs: update documentation` - Documentation changes
- `test: add tests` - Test additions
- `refactor: improve code structure` - Code refactoring
- `chore: update dependencies` - Maintenance tasks

## Review Process

1. All PRs require at least one review
2. CI checks must pass (tests, linting)
3. Documentation must be updated if applicable
4. Breaking changes must be clearly documented

## Questions?

Feel free to open an issue for any questions about contributing.

Thank you for contributing!
