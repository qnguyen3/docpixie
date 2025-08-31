#!/usr/bin/env python3
"""
DocPixie CLI - Modern terminal interface for document chat
"""

import sys


def main():
    """Main entry point for DocPixie CLI"""
    try:
        # Try to import and use the new Textual CLI
        from docpixie.cli.app import main as textual_main
        textual_main()
    except ImportError as e:
        # Fallback to legacy CLI if Textual is not installed
        print("Note: Textual not installed. Using legacy CLI.")
        print("Install with: pip install textual>=0.47.0")
        print("")
        
        from docpixie.cli.legacy import main as legacy_main
        legacy_main()


if __name__ == "__main__":
    main()
