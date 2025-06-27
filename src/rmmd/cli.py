"""Command-line interface."""

import click
from pydantic import ValidationError
from .schema import Schema
import yaml


@click.group()
def rmmd():
    """RMMD CLI main function."""
    pass


@rmmd.command("validate")
@click.argument("model_file", type=click.File("r", encoding="utf-8"))
@click.option(
    "-o",
    "--option",
    default=0,
    show_default=True,
    help="This is a dummy option to show how to add them with click.",
)
def validate(model_file, option: int):
    """Validate MODEL_FILE against RMMD schema."""
    print(f"You requested to validate {model_file}...")
    print(f"Option value: {option}")

    content = yaml.safe_load(model_file)
    try:
        Schema.model_validate(content)
    except ValidationError as e:
        print("Validation failed:")
        print(e)
        return 1
    else:
        print("Validation succeeded.")
        return 0
