from pathlib import Path
import argparse

from PIL import Image


def main(args):
    filename = args.input_path.stem
    output_path = args.input_path.parent / f"{filename}_resized{args.input_path.suffix}"
    with Image.open(args.input_path) as image:
        resized_img = image.resize((args.width, args.height))
        resized_img.save(output_path)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Resize an image to the specified dimensions.')
    parser.add_argument('--input-path', '-i', type=Path, help='Path to the input image')
    parser.add_argument('--width', type=int, default=640, help='Width of the resized image')
    parser.add_argument('--height', type=int, default=640, help='Height of the resized image')
    args = parser.parse_args()

    exit(main(args))