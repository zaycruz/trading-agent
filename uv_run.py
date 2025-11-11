#!/usr/bin/env python3
"""
UV-powered test runner and development script for Trading Arena
"""

import sys
import subprocess
import argparse
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


def setup_project():
    """Set up the project with uv"""
    print(" Setting up Trading Arena with UV")

    # Check if uv is installed
    if not run_uv_command(["--version"], "Checking UV installation", check=False):
        print("-  UV not found. Please install UV:")
        print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("  # or on Windows:"
        print("  powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"")
        return False

    # Create virtual environment
    if not run_uv_command(["venv"], "Creating virtual environment"):
        print("WARNING:   Virtual environment may already exist")

    # Install dependencies
    if not run_uv_command(["sync"], "Installing dependencies"):
        print("-  Failed to install dependencies")
        return False

    # Install development dependencies
    if not run_uv_command(["sync", "--group", "dev"], "Installing dev dependencies"):
        print("-  Failed to install dev dependencies")
        return False

    # Install test dependencies
    if not run_uv_command(["sync", "--group", "test"], "Installing test dependencies"):
        print("-  Failed to install test dependencies")
        return False

    print("-  Project setup complete!")
    return True


def run_tests(args):
    """Run tests with uv"""
    test_cmd = ["run", "pytest"]

    if args.unit_only:
        test_cmd.extend(["-m", "not integration"])
    elif args.integration_only:
        test_cmd.extend(["tests/test_integration.py", "-v"])
    else:
        test_cmd.append("tests/")

    if args.coverage:
        test_cmd.extend(["--cov=src", "--cov-report=term-missing"])
        if args.html_coverage:
            test_cmd.append("--cov-report=html")

    if args.verbose:
        test_cmd.append("-v")

    if args.file:
        test_cmd.append(args.file)

    return run_uv_command(test_cmd, "Running tests")


def lint_code():
    """Run linting tools"""
    success = True

    # Run black
    if not run_uv_command(["run", "black", "--check", "src/", "tests/"], "Checking code formatting with Black"):
        success = False

    # Run isort
    if not run_uv_command(["run", "isort", "--check-only", "src/", "tests/"], "Checking import sorting with isort"):
        success = False

    # Run ruff
    if not run_uv_command(["run", "ruff", "check", "src/", "tests/"], "Running ruff linter"):
        success = False

    # Run mypy
    if not run_uv_command(["run", "mypy", "src/"], "Running mypy type checker"):
        success = False

    if success:
        print("-  All linting checks passed!")
    else:
        print("-  Some linting checks failed. Run 'python uv_run.py format' to fix formatting.")

    return success


def format_code():
    """Format code with black and isort"""
    success = True

    # Run black
    if not run_uv_command(["run", "black", "src/", "tests/"], "Formatting code with Black"):
        success = False

    # Run isort
    if not run_uv_command(["run", "isort", "src/", "tests/"], "Sorting imports with isort"):
        success = False

    if success:
        print("-  Code formatted successfully!")

    return success


def run_application():
    """Run the trading application"""
    return run_uv_command(["run", "python", "-m", "src.main"], "Running Trading Arena")


def add_dependency(args):
    """Add a dependency"""
    cmd = ["add"]
    if args.dev:
        cmd.extend(["--group", "dev"])
    elif args.test:
        cmd.extend(["--group", "test"])
    elif args.docs:
        cmd.extend(["--group", "docs"])
    elif args.lint:
        cmd.extend(["--group", "lint"])

    cmd.append(args.package)

    return run_uv_command(cmd, f"Adding dependency: {args.package}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="UV-powered Trading Arena development tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up the project")

    # Test commands
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("--unit-only", action="store_true", help="Run unit tests only")
    test_parser.add_argument("--integration-only", action="store_true", help="Run integration tests only")
    test_parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    test_parser.add_argument("--html-coverage", action="store_true", help="Generate HTML coverage report")
    test_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    test_parser.add_argument("--file", "-f", help="Run specific test file")

    # Lint commands
    lint_parser = subparsers.add_parser("lint", help="Run linting checks")
    format_parser = subparsers.add_parser("format", help="Format code")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run the application")

    # Add dependency command
    add_parser = subparsers.add_parser("add", help="Add a dependency")
    add_parser.add_argument("package", help="Package to add")
    add_parser.add_argument("--dev", action="store_true", help="Add to dev dependencies")
    add_parser.add_argument("--test", action="store_true", help="Add to test dependencies")
    add_parser.add_argument("--docs", action="store_true", help="Add to docs dependencies")
    add_parser.add_argument("--lint", action="store_true", help="Add to lint dependencies")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("-  Error: pyproject.toml not found. Please run from project root.")
        sys.exit(1)

    # Change to project root if needed
    os.chdir(Path(__file__).parent)

    success = True

    if args.command == "setup":
        success = setup_project()
    elif args.command == "test":
        success = run_tests(args)
    elif args.command == "lint":
        success = lint_code()
    elif args.command == "format":
        success = format_code()
    elif args.command == "run":
        success = run_application()
    elif args.command == "add":
        success = add_dependency(args)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()