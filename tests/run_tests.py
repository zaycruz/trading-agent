#!/usr/bin/env python3
"""
Test runner script for Trading Arena tests using UV
"""

import sys
import subprocess
import os
from pathlib import Path


def run_uv_command(cmd, description, check=True):
    """Run a uv command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: uv {' '.join(cmd)}")
    print('='*60)

    try:
        full_cmd = ["uv"] + cmd
        result = subprocess.run(full_cmd, check=check, capture_output=False)
        if result.returncode == 0:
            print(f"-  {description} completed successfully")
            return True
        else:
            print(f"-  {description} failed with exit code {result.returncode}")
            return False
    except subprocess.CalledProcessError as e:
        print(f"-  {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"-  'uv' command not found. Please install uv: https://docs.astral.sh/uv/")
        return False


def check_uv_installation():
    """Check if uv is installed and project is set up"""
    print(" Checking UV installation...")

    # Check if uv is available
    if not run_uv_command(["--version"], "Checking UV", check=False):
        print("-  UV not found. Please install UV:")
        print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("  # or on Windows:")
        print("  powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"")
        return False

    # Check if virtual environment exists
    if not Path(".venv").exists():
        print("WARNING:   Virtual environment not found. Setting up...")
        if not run_uv_command(["venv"], "Creating virtual environment"):
            return False

    # Check if dependencies are installed
    if not run_uv_command(["sync", "--group", "test"], "Installing test dependencies", check=False):
        print("-  Failed to install dependencies")
        return False

    return True


def main():
    """Main test runner"""
    print(" Trading Arena Test Runner (UV Edition)")
    print("=" * 60)

    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("-  Error: pyproject.toml not found. Please run from project root.")
        sys.exit(1)

    # Check UV installation and setup
    if not check_uv_installation():
        sys.exit(1)

    # Change to project root if needed
    os.chdir(Path(__file__).parent)

    success_count = 0
    total_tests = 0

    # Test 1: Import test
    if run_uv_command([
        "run", "python", "test_imports.py"
    ], "Import verification"):
        success_count += 1
    total_tests += 1

    # Test 2: Test collection check
    if run_uv_command([
        "run", "pytest", "tests/", "--collect-only"
    ], "Test collection check"):
        success_count += 1
    total_tests += 1

    # Test 3: Run unit tests
    if run_uv_command([
        "run", "pytest", "tests/", "-v", "-m", "not integration"
    ], "Unit tests"):
        success_count += 1
    total_tests += 1

    # Test 4: Run integration tests
    if run_uv_command([
        "run", "pytest", "tests/test_integration.py", "-v"
    ], "Integration tests"):
        success_count += 1
    total_tests += 1

    # Test 5: Run all tests with coverage
    if run_uv_command([
        "run", "pytest", "tests/", "--cov=src", "--cov-report=term-missing", "--cov-report=html"
    ], "All tests with coverage"):
        success_count += 1
    total_tests += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"🏁 Test Summary")
    print('='*60)
    print(f"Passed: {success_count}/{total_tests} test suites")

    if success_count == total_tests:
        print("All tests passed!")
        sys.exit(0)
    else:
        print(f"-  {total_tests - success_count} test suite(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()