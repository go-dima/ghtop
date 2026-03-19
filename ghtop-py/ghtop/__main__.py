import argparse
from pathlib import Path
from ghtop.app import GHTopApp


def main():
    parser = argparse.ArgumentParser(prog="ghtop")
    parser.add_argument(
        "--config", metavar="PATH", type=Path,
        help="Path to config file (default: ~/.config/ghtop/config.yaml)"
    )
    args = parser.parse_args()
    GHTopApp(config_path=args.config).run()


if __name__ == "__main__":
    main()
