import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from .schema import Schema


def read_json(path: Path) -> dict:
    with open(path, 'r', encoding='utf-8') as file:
        return json.load(file)

def read_file(path: Path) -> dict:
    match path.suffix:
        case ".json":
            return read_json(path)
        case _:
            raise ValueError(f"Unsupported file format: {path.suffix}")

def main():
    parser = argparse.ArgumentParser(
                description="Reaction model metadata schema.")
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser(
                            "validate",
                            help="Validate a file.")
    validate_parser.add_argument("file",
                                 help="Path to the file to validate.",
                                 type=Path)

    args = parser.parse_args()
    if args.command == "validate":
        print(f"Validating {args.file}")

        data = read_file(args.file)
        try:
            Schema(**data)
        except ValidationError as e:
            print(f"Validation failed: {e}")
            exit(1)

        print("Validation successful.")

if __name__ == "__main__":
    main()