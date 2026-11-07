"""Command line entry point. No GUI import required."""

import argparse

from studio_ia import __version__


def main() -> None:
    parser = argparse.ArgumentParser(description="STUDIO IA — restauration vidéo locale")
    parser.add_argument("--version", action="version", version=__version__)
    parser.parse_args()


if __name__ == "__main__":
    main()
