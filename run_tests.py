#!/usr/bin/env python3
"""
Test runner script for Trading Arena tests
"""

import sys
import subprocess
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        return False


def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")

    required_packages = [
        "pytest",
        "alpaca-py",
        "pandas",
        "numpy",
        "pydantic",
        "python-dotenv"
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (missing)")
            missing_packages.append(package)

    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install -r requirements.txt")
        return False

    return True


def main():
    """Main test runner"""
    print("🚀 Trading Arena Test Runner")
    print("=" * 60)

    # Check if we're in the right directory
    if not Path("src/tools.py").exists():
        print("❌ Error: src/tools.py not found. Please run from project root.")
        sys.exit(1)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Change to project root if needed
    os.chdir(Path(__file__).parent)

    success_count = 0
    total_tests = 0

    # Test 1: Import test
    if run_command([
        sys.executable, "test_imports.py"
    ], "Import verification"):
        success_count += 1
    total_tests += 1

    # Test 2: Code formatting check (optional)
    if run_command([
        sys.executable, "-m", "pytest", "tests/", "-k", "test_", "--collect-only"
    ], "Test collection check"):
        success_count += 1
    total_tests += 1

    # Test 3: Run unit tests
    if run_command([
        sys.executable, "-m", "pytest", "tests/", "-v", "-m", "not integration"
    ], "Unit tests"):
        success_count += 1
    total_tests += 1

    # Test 4: Run integration tests
    if run_command([
        sys.executable, "-m", "pytest", "tests/test_integration.py", "-v"
    ], "Integration tests"):
        success_count += 1
    total_tests += 1

    # Test 5: Run all tests with coverage (if coverage is available)
    try:
        if run_command([
            sys.executable, "-m", "pytest", "tests/", "--cov=src", "--cov-report=term-missing", "--cov-report=html"
        ], "All tests with coverage"):
            success_count += 1
        total_tests += 1
    except:
        print("⚠️  Coverage not available. Install with: pip install pytest-cov")
        # Run all tests without coverage
        if run_command([
            sys.executable, "-m", "pytest", "tests/", "-v"
        ], "All tests"):
            success_count += 1
        total_tests += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"🏁 Test Summary")
    print('='*60)
    print(f"Passed: {success_count}/{total_tests} test suites")

    if success_count == total_tests:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"❌ {total_tests - success_count} test suite(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()