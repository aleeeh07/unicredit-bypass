# 🚀 Unicredit Startup Your Life Task Automator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/playwright-1.30+-green.svg)](https://playwright.dev/)

Automatically unlock and complete all tasks and lessons in the Unicredit Startup Your Life educational platform, saving you hours of tedious clicking.

## 🔍 What it does

This tool automates the process of completing learning modules in the Unicredit Startup Your Life platform by:

- Logging into your account securely
- Navigating through each module in the specified curriculum
- Systematically marking each lesson as viewed and completed
- Handling special cases like first and last lessons in modules
- Implementing intelligent retry mechanisms for failed attempts
- Providing detailed progress logs throughout the process

## ✨ Features

- **Efficient Automation**: Completes all lessons in minutes instead of hours
- **Two-Phase Processing**: Special handling for regular lessons and module-ending lessons
- **Robust Error Handling**: Retries failed operations with progressively longer delays
- **Progress Tracking**: Detailed console output showing completion status
- **Headful Mode**: Watch the browser as it works through your modules
- **Configurable Modules**: Easily select which modules to complete

## 📋 Prerequisites

- Python 3.7 or higher
- Playwright for Python
- Valid Unicredit Startup Your Life account credentials

## 🔧 Installation

```bash
# Clone the repository
git clone https://github.com/aleeeh07/unicredit-bypass.git
cd unicredit-bypass

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install playwright asyncio
playwright install chromium
```

## 🚀 Usage

Run the script with your login credentials:

```bash
python automator.py --username your.email@example.com --password yourpassword
```

### Customizing modules

To select which modules to complete, edit the `modules_data` dictionary in the script:

```python
modules_data = {
    "310": [659, 660, 661, 662, 663, 664, 665, 666, 667],
    "311": [668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679],
    # Add or remove modules as needed
}
```

## ❗ Common Errors and Solutions

| Error | Meaning | Solution |
|-------|---------|----------|
| `XSRF token not found` | Failed to capture authentication token | Try clearing browser cookies and cache, then run again |
| `Failed: Unauthorized access` | Invalid credentials or session expired | Verify your username and password are correct |
| `TimeoutError` | Page took too long to load | Check your internet connection and try again |
| `Error loading module page` | Module might be inaccessible | Verify the module exists and you have access to it |
| `Retry failed for lesson` | Multiple attempts to unlock lesson failed | The platform might be experiencing issues, try again later |

## 🔄 How it Works

1. The script launches a browser and logs into the platform
2. It captures the authentication token needed for API requests
3. Phase 1: Processes all regular lessons in each module
   - Visits each lesson page
   - Sends API requests to mark content as viewed
   - Marks each lesson as completed
4. Phase 2: Handles the final lesson of each module (which requires special processing)
5. Reports detailed statistics on successful completions

## ⚠️ Disclaimer

This tool is meant for educational purposes only and should be used responsibly. Use it only to complete your own curriculum that you intend to study. The author is not responsible for any misuse or violations of terms of service.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
