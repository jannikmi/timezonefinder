#!/usr/bin/env python3

"""Shared utilities for benchmark reporting and RST generation.

This module contains common functionality used by various benchmark scripts
to generate RST reports and handle CLI interfaces.
"""

import argparse
import platform
from pathlib import Path
from typing import List, Dict, Any

import numpy as np

from scripts.reporting import (
    redirect_output_to_file_contextmanager,
    print_rst_table,
    rst_title,
)
from timezonefinder import TimezoneFinder


class BenchmarkReporter:
    """Helper class for generating benchmark RST reports with a fluent API."""

    def __init__(self, title: str, output_path: Path):
        self.title = title
        self.output_path = Path(output_path)
        self.content = []

    def add_section(self, title: str, level: int = 1):
        """Add a new section with the given title and RST level."""
        self.content.append(("section", title, level))
        return self

    def add_text(self, text: str):
        """Add text content."""
        self.content.append(("text", text))
        return self

    def add_table(self, headers: List[str], rows: List[List[str]]):
        """Add a table to the report."""
        self.content.append(("table", headers, rows))
        return self

    def add_note(self, text: str):
        """Add a note directive."""
        self.content.append(("note", text))
        return self

    def write_report(self):
        """Write the complete report to the output file."""
        print(f"Writing {self.title.lower()} report to: {self.output_path}")

        with redirect_output_to_file_contextmanager(self.output_path):
            print(rst_title(self.title, 0))
            print()

            for item in self.content:
                if item[0] == "section":
                    _, title, level = item
                    print(rst_title(title, level))
                    print()
                elif item[0] == "text":
                    _, text = item
                    print(text)
                    if text:  # Only add newline if not empty string
                        print()
                elif item[0] == "table":
                    _, headers, rows = item
                    print_rst_table(headers, rows)
                    print()
                elif item[0] == "note":
                    _, text = item
                    print(".. note::")
                    print()
                    print(f"   {text}")
                    print()


def create_cli_parser(
    description: str, script_name: str = None
) -> argparse.ArgumentParser:
    """Create a standardized CLI parser for benchmark scripts."""
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Run benchmarks with console output
  %(prog)s --rst             # Generate RST report file
        """,
    )

    parser.add_argument(
        "--rst",
        action="store_true",
        help="Generate RST format report file instead of console output",
        default=True,
    )

    return parser


def format_performance_result(
    name: str, time_per_query: float, queries_per_second: float
) -> List[str]:
    """Format performance results for table display."""
    return [
        name,
        f"{time_per_query:.1e}",
        f"{queries_per_second:.1e}"
        if queries_per_second >= 1000
        else f"{queries_per_second / 1000:.0f}k",
    ]


def calculate_speedup(time1: float, time2: float, name1: str, name2: str) -> str:
    """Calculate and format speedup comparison between two implementations."""
    if time1 < time2:
        speedup = (time2 / time1) - 1
        return f"{name1} is {speedup:.1f}x faster than {name2}"
    else:
        speedup = (time1 / time2) - 1
        return f"{name2} is {speedup:.1f}x faster than {name1}"


def print_progress(current: int, total: int, prefix: str = "Progress"):
    """Print progress updates during long-running operations."""
    if total > 0:
        percent = int((current / total) * 100)
        if percent % 10 == 0 and current > 0:
            print(f"{prefix}: {percent}%")


def get_system_status() -> Dict[str, Any]:
    """Get comprehensive system status information for benchmark reports."""
    tf_instance = TimezoneFinder()

    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "platform_processor": platform.processor() or "Unknown",
        "numpy_version": np.__version__,
        "using_clang_pip": tf_instance.using_clang_pip(),
        "using_numba": tf_instance.using_numba(),
        "timezonefinder_version": getattr(tf_instance, "__version__", "Unknown"),
    }


def add_system_status_section(
    reporter: BenchmarkReporter, additional_info: Dict[str, Any] = None
):
    """Add a comprehensive system status section to a benchmark report."""
    system_info = get_system_status()

    reporter.add_section("System Status")

    # Python environment
    reporter.add_section("Python Environment", level=2)
    reporter.add_text(
        f"**Python Version**: {system_info['python_version']} ({system_info['python_implementation']})"
    )
    reporter.add_text(f"**NumPy Version**: {system_info['numpy_version']}")
    reporter.add_text(
        f"**Platform**: {system_info['platform_system']} {system_info['platform_machine']}"
    )
    if system_info["platform_processor"] != "Unknown":
        reporter.add_text(f"**Processor**: {system_info['platform_processor']}")

    # TimezoneFinder configuration
    reporter.add_section("TimezoneFinder Configuration", level=2)
    reporter.add_text(
        f"**C Implementation Available**: {system_info['using_clang_pip']}"
    )
    reporter.add_text(f"**Numba JIT Available**: {system_info['using_numba']}")

    # Performance optimizations status
    reporter.add_section("Performance Optimizations", level=2)
    optimizations = []
    if system_info["using_clang_pip"]:
        optimizations.append("✓ Compiled C extension for point-in-polygon operations")
    else:
        optimizations.append("✗ Using pure Python point-in-polygon implementation")

    if system_info["using_numba"]:
        optimizations.append("✓ Numba JIT compilation enabled")
    else:
        optimizations.append("✗ Numba JIT compilation not available")

    for opt in optimizations:
        reporter.add_text(f"* {opt}")

    # Additional benchmark-specific information
    if additional_info:
        reporter.add_section("Benchmark Configuration", level=2)
        for key, value in additional_info.items():
            if isinstance(value, (int, float)) and value >= 1000:
                formatted_value = f"{value:,}"
            else:
                formatted_value = str(value)
            reporter.add_text(f"**{key.replace('_', ' ').title()}**: {formatted_value}")

    return reporter
