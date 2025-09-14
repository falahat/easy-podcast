# Testing Guide for the Podcast Manager Package

This document provides a comprehensive guide to understanding, running, and writing tests for this project. It is intended for both human developers and AI agents to ensure consistency and maintain high code quality.

## Testing Overview

The testing philosophy in this project centers on fast, reliable, and isolated unit tests. We use `pytest` as our testing framework.

A critical part of our testing strategy involves mocking heavy external libraries, particularly for the transcription components. This ensures that tests can run quickly on any machine without requiring a GPU or downloading large AI models.

## Running Tests

There are two primary ways to run tests:

### 1. Using VS Code Testing Tools (MCP Servers)

The recommended way to run tests during development is through the VS Code editor's built-in testing sidebar. These tools are powered by Model Context Protocol (MCP) servers that integrate directly with the IDE.

- **Run Tests**: Use the "Run Tests" button in the Testing view.
- **Debug Tests**: Use the "Debug Tests" button to step through code.

> **Warning: Test Discovery Failures**
> Occasionally, `pytest`'s test discovery mechanism can fail silently. This may cause the testing tools to report **0 tests found** and therefore **0 failures**, giving a false sense of security. If you see 0 tests have run, always fall back to the command line to verify.

### 2. Using the Command Line with `pytest`

To get a definitive test run and ensure all tests are being discovered correctly, you should periodically run `pytest` from the command line.

> **IMPORTANT: Activate the Virtual Environment!**
> Before running any commands, you **must** activate the virtual environment. Forgetting this step is the most common cause of `ModuleNotFoundError` or other import errors.

First, ensure your virtual environment is activated:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then, run `pytest`:

```powershell
pytest
```

You can also run specific test files or even specific tests:

```powershell
# Run all tests in a file
pytest tests/transcription/test_diarizer.py

# Run a specific test class
pytest tests/transcription/test_diarizer.py::TestDiarizer

# Run a specific test function
pytest tests/transcription/test_diarizer.py::TestDiarizer::test_diarizer_speaker_assignment
```

## Transcription Mocks: The Core of Our Test Setup

The most complex part of our test suite is the mocking system for the external `easy-whisperx` library.

### Why We Mock

The transcription components rely on heavy libraries:
- `whisperx`: For transcription, alignment, and diarization.
- `easy-whisperx`: External transcription library that manages torch dependencies.

Running these in a test environment would be slow, resource-intensive, and require specialized hardware. We mock them to test our application's logic in isolation.

### How Mocks Work: `tests/transcription/conftest.py`

All transcription-related mocks are defined in `tests/transcription/conftest.py` using a `pytest` fixture with `autouse=True`.

```python
@pytest.fixture(autouse=True)
def mock_transcription_imports() -> Generator[Dict[str, MagicMock], None, None]:
    # ...
```

This fixture automatically runs for every test in the `tests/transcription` directory.

**The Key Mechanism: `unittest.mock.patch`**

The fixture uses `unittest.mock.patch` to intercept imports *where they are used in the application source code*. This is the most critical concept to understand.

**✅ CORRECT:**
```python
# This patches 'whisperx' as it is imported inside the 'easy_whisperx' modules.
patch("easy_whisperx.diarizer.whisperx", mock_whisperx)
```

**❌ INCORRECT:**
```python
# This will NOT work because the test's 'whisperx' is a different object
# from the one imported by the application code.
patch("whisperx", mock_whisperx)
```

### How to Use the Mocks in Your Tests

The `autouse` fixture handles the patching, but your test function needs to "request" the mock object to interact with it. This is done by adding it as a parameter to your test function.

**Available Fixtures:**
- `mock_whisperx`: The master `MagicMock` for the `whisperx` library.
- `mock_torch`: The master `MagicMock` for the `torch` library.
- `mock_diarization_pipeline`: A mock for the `DiarizationPipeline` class instance.

**Example:**

```python
from unittest.mock import MagicMock

# Request the mock_whisperx fixture by adding it as a parameter
def test_something_with_whisperx(mock_whisperx: MagicMock):
    # Your test code here...

    # Now you can make assertions against the mock
    mock_whisperx.load_model.assert_called_once()
```

## Common Gotchas & Troubleshooting

If your tests are failing, check for these common issues first.

#### 1. `NameError: name 'mock_whisperx' is not defined`
**Cause**: You are trying to use `mock_whisperx` (or another mock) in your test, but you forgot to add it to the test function's signature.
**Fix**: Add the mock fixture as a parameter.
```python
# WRONG
def test_my_feature():
    mock_whisperx.do_something() # -> NameError

# RIGHT
def test_my_feature(mock_whisperx: MagicMock):
    mock_whisperx.do_something()
```

#### 2. `AssertionError: Expected 'mock' to have been called once. Called 0 times.`
**Cause**: Your test expected a function to be called, but it wasn't. This is often due to an incorrect patch target in `conftest.py` or a logic error in the application code.
**Fix**:
1.  Verify the patch target in `conftest.py` matches the import location in the source file (e.g., `easy_whisperx.MY_MODULE.whisperx`).
2.  Debug the test to ensure the code path leading to the function call is being executed as you expect.

#### 3. Importing Real Libraries in Tests
**Cause**: A test file contains `import whisperx` or `import torch`. This bypasses the mocking system entirely and will likely lead to errors or attempt to load real models.
**Fix**: Remove all direct imports of `whisperx` and `torch` from your test files. Rely exclusively on the fixtures provided by `conftest.py`.

## Test Coverage

We aim for high test coverage to ensure code quality. You can generate a coverage report from the command line.

### Generating a Coverage Report

Run `pytest` with the `--cov` flag. For branch coverage, add `--cov-branch`.

```powershell
# Generate a report and show missing lines in the terminal
pytest --cov=src/easy_podcast --cov-branch --cov-report=term-missing

# Generate a browsable HTML report
pytest --cov=src/easy_podcast --cov-branch --cov-report=html
```

After running the HTML report command, you can view the results by opening `htmlcov/index.html` in your browser. This interactive report allows you to drill down into each file and see exactly which lines and branches are not covered by tests.