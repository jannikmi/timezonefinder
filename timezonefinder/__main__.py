"""Allow ``python -m timezonefinder`` to invoke the CLI entry point."""

from timezonefinder.command_line import main

if __name__ == "__main__":
    main()
