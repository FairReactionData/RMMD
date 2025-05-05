"""Command-line interface."""

import click


@click.group()
def rmmd():
    """RMMD CLI main function."""
    pass


@rmmd.command("validate")
@click.argument("model_file")
@click.option(
    "-o",
    "--option",
    default=0,
    show_default=True,
    help="This is a dummy option to show how to add them with click.",
)
def validate(model_file: str, option: int):
    """Validate MODEL_FILE against RMMD schema."""
    print(f"You requested to validate {model_file}...")
    print(f"Option value: {option}")
