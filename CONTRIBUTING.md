# Contributing to Overtime

First off, thank you for considering contributing to the Overtime app! It's people like you that make this project better for everyone.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Pull Requests](#pull-requests)
- [Development Setup](#development-setup)
- [Style Guidelines](#style-guidelines)
- [Commit Messages](#commit-messages)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

This project and everyone participating in it is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to ar.frappe.dev@gmail.com.

## Getting Started

Before you begin:

- Make sure you have a [GitHub account](https://github.com/signup)
- Check if an issue already exists for what you want to work on
- Fork the repository to your own GitHub account
- Clone the fork to your local machine

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues as you might find that you don't need to create one. When you are creating a bug report, please include as many details as possible.

**Before Submitting A Bug Report:**

- Check the [troubleshooting section](README.md#troubleshooting) in the README
- Verify you're using the latest version of the app
- Search existing issues to see if the problem has already been reported

**How Do I Submit A (Good) Bug Report?**

Bugs are tracked as [GitHub issues](https://github.com/aliraxa29/overtime/issues). Create an issue and provide the following information:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples** (include code snippets, log output, screenshots)
- **Describe the behavior you observed and what you expected**
- **Include your environment details:**
  - Frappe version
  - HRMS version
  - Python version
  - Browser (if applicable)

### Suggesting Enhancements

Enhancement suggestions are tracked as [GitHub issues](https://github.com/aliraxa29/overtime/issues). When creating an enhancement suggestion, please include:

- **Use a clear and descriptive title**
- **Provide a step-by-step description** of the suggested enhancement
- **Explain why this enhancement would be useful**
- **List any alternatives you've considered**

### Pull Requests

The process described here aims to:

- Maintain the project's quality
- Fix problems that are important to users
- Engage the community in working toward the best possible product

Please follow these steps:

1. **Fork the repository** and create your branch from `develop`
2. **If you've added code**, add tests that cover your changes
3. **If you've changed APIs**, update the documentation
4. **Ensure the test suite passes**
5. **Make sure your code follows the style guidelines**
6. **Issue your pull request**

## Development Setup

### Prerequisites

- Python 3.10+
- Frappe Bench v15+
- HRMS v15 installed

### Setup Steps

```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/overtime.git

# 2. Add the app to your bench
cd ~/frappe-bench
bench get-app /path/to/overtime

# 3. Install the app on your site
bench --site your-site.local install-app overtime

# 4. Install pre-commit hooks
cd apps/overtime
pip install pre-commit
pre-commit install

# 5. Create a new branch for your changes
git checkout -b feature/your-feature-name
```

### Running the Development Server

```bash
# Start the development server
bench start

# Or run specific services
bench serve            # Web server
bench watch           # Watch for file changes
```

## Style Guidelines

### Python Code Style

We use [ruff](https://github.com/astral-sh/ruff) for linting and formatting Python code.

```bash
# Run ruff linter
ruff check .

# Run ruff formatter
ruff format .

# Fix import sorting
ruff check --select=I --fix .
```

**Key Guidelines:**

- Use tabs for indentation (Frappe convention)
- Maximum line length: 110 characters
- Use double quotes for strings
- Follow PEP 8 naming conventions

### JavaScript Code Style

We use [ESLint](https://eslint.org/) and [Prettier](https://prettier.io/) for JavaScript.

```bash
# Run ESLint
npx eslint .

# Run Prettier
npx prettier --write .
```

### Pre-commit Hooks

All code style checks run automatically via pre-commit hooks:

```bash
# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

## Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:**

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvements
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools

**Examples:**

```
feat(shift-rule): add support for custom rate multipliers per department

fix(overnight): correctly calculate hours when shift crosses midnight

docs: update installation instructions for v15

refactor(utils): simplify overtime calculation logic
```

## Testing

### Running Tests

```bash
# Run all tests
bench --site your-site.local run-tests --app overtime

# Run specific test file
bench --site your-site.local run-tests --module overtime.overtime.doctype.overtime_entry.test_overtime_entry

# Run with verbose output
bench --site your-site.local run-tests --app overtime -v
```

### Writing Tests

- Place tests in `test_*.py` files alongside the module being tested
- Use Frappe's `FrappeTestCase` as the base class
- Include both positive and negative test cases
- Test edge cases (overnight shifts, Ramadan period, etc.)

Example:

```python
import frappe
from frappe.tests.utils import FrappeTestCase

class TestOvertimeEntry(FrappeTestCase):
    def setUp(self):
        # Setup test data
        pass

    def test_overtime_calculation(self):
        # Test implementation
        result = calculate_overtime(...)
        self.assertEqual(result, expected_value)
```

## Documentation

### Updating Documentation

- Update the README.md for user-facing changes
- Add docstrings to new functions and classes
- Update the CHANGELOG.md for notable changes

### Docstring Format

Use Google-style docstrings:

```python
def calculate_overtime(attendance, shift_rule):
    """Calculate overtime hours for an attendance record.

    Args:
        attendance: The Attendance document.
        shift_rule: The matched Overtime Shift Rule.

    Returns:
        float: The calculated overtime hours.

    Raises:
        ValueError: If attendance has no checkin records.
    """
    pass
```

## Questions?

If you have questions about contributing, feel free to open an issue with the `question` label or reach out to the maintainers.

Thank you for contributing! 🎉
