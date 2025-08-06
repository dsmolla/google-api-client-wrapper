#!/usr/bin/env python3
"""
Test runner script for Google API Client tests.

This script provides convenient commands to run different test suites.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str]) -> int:
    """Run a command and return the exit code."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def main():
    """Main test runner function."""
    if len(sys.argv) < 2:
        print("""
Usage: python run_tests.py <command>

Available commands:
  all                 - Run all tests
  unit               - Run only unit tests
  integration        - Run only integration tests
  gmail              - Run Gmail-related tests
  calendar           - Run Calendar-related tests
  async              - Run async tests
  sync               - Run non-async tests
  coverage           - Run tests with coverage report
  gmail-unit         - Run Gmail unit tests
  calendar-unit      - Run Calendar unit tests
  gmail-integration  - Run Gmail integration tests
  calendar-integration - Run Calendar integration tests

Examples:
  python run_tests.py unit
  python run_tests.py gmail
  python run_tests.py coverage
        """)
        return 1

    command = sys.argv[1].lower()
    
    # Base pytest command
    base_cmd = [sys.executable, "-m", "pytest"]
    
    if command == "all":
        cmd = base_cmd
    elif command == "unit":
        cmd = base_cmd + ["-m", "unit"]
    elif command == "integration":
        cmd = base_cmd + ["-m", "integration"]
    elif command == "gmail":
        cmd = base_cmd + ["-m", "gmail"]
    elif command == "calendar":
        cmd = base_cmd + ["-m", "calendar"]
    elif command == "async":
        cmd = base_cmd + ["-m", "asyncio"]
    elif command == "sync":
        cmd = base_cmd + ["-m", "not asyncio"]
    elif command == "coverage":
        cmd = base_cmd + ["--cov=src", "--cov-report=html", "--cov-report=term-missing"]
    elif command == "gmail-unit":
        cmd = base_cmd + ["-m", "unit and gmail"]
    elif command == "calendar-unit":
        cmd = base_cmd + ["-m", "unit and calendar"]
    elif command == "gmail-integration":
        cmd = base_cmd + ["-m", "integration and gmail"]
    elif command == "calendar-integration":
        cmd = base_cmd + ["-m", "integration and calendar"]
    else:
        print(f"Unknown command: {command}")
        return 1
    
    return run_command(cmd)


if __name__ == "__main__":
    sys.exit(main())