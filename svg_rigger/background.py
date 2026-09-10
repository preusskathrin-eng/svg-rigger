"""Optional step 00: remove a raster background before vectorization."""

import argparse
from pathlib import Path


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def remove_background(input_path, output_path, model=None):
    try:
        from PIL import Image
        from rembg import new_session, remove
    except ImportError as exc:
        raise RuntimeError(
            "background removal is optional; install it with "
            "'python -m pip install -e .[background]'"
        ) from exc

    input_path = Path(input_path)
    output_path = Path(output_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"input image not found: {input_path}")
    if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"unsupported input format {input_path.suffix!r}; expected PNG, JPEG or WebP"
        )
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    session = new_session(model) if model else None
    with Image.open(input_path) as image:
        result = remove(image.convert("RGBA"), session=session)
        result.save(output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_image", help="Input PNG, JPEG or WebP")
    parser.add_argument("output_png", help="New transparent PNG")
    parser.add_argument(
        "--model",
        help="Optional rembg model name; omission uses the installed rembg default",
    )
    args = parser.parse_args()
    try:
        output = remove_background(args.input_image, args.output_png, args.model)
    except (FileNotFoundError, FileExistsError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    print(f"[00] Background removed: {output}")


if __name__ == "__main__":
    main()
