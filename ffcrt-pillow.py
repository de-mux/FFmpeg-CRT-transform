#!/usr/bin/env python

"""Attempt to implement CRT filter using PIL (Pillow)."""


import math
import re
from pathlib import Path
import tempfile
import warnings
import types
from typing import Tuple, Union

import click
from PIL import Image, ImageChops, ImageOps, ImageEnhance, ImageMath, ImageFilter

GAMMA_CORRECTION = 2.2


def to_python_type(token):
    if token.lower() == "yes":
        return True
    elif token.lower() == "no":
        return False

    # fractions
    fraction_re = re.match(r"(\d+)\s*?/\s*?(\d+)", token.lower())
    if fraction_re:
        frac = fraction_re.groups()
        return float(frac[0]) / float(frac[1])

    try:
        return float(token)
    except ValueError:
        return token.lower()


def read_config_file(config_file):
    params = types.SimpleNamespace()
    with open(config_file, "rb") as fp:
        for line in fp:
            line = str(line, encoding="UTF-8").strip()
            result = re.findall(r"^([^;][^\s]+)\s+([^\s]+)", line)
            if result:
                key, value = result[0]
                key = key if key[0].isalpha() else "_" + key
                params.__dict__[key.lower()] = to_python_type(value)
    return params


def adjust_params(params, ix: int, iy: int):
    if params.oaspect:
        warnings.warn("OASPECT is not supported")
    if params.omargin:
        warnings.warn("OMARGIN is not supported")
    if params.crt_curvature:
        warnings.warn("CRT_CURVATURE not implemented")
    if params.bezel_curvature:
        warnings.warn("BEZEL_CURVATURE not implemented")
    if params._16bpc_processing:
        warnings.warn("16BPC_PROCESSING not implemented")
    if params.flat_panel:
        warnings.warn("FLAT_PANEL not implemented")
    # 8-bit processing
    params.max = 255  # rng = 256
    params.half = 128
    params.rgbfmt = "rgb24"
    params.kludgefmt = "rgb24"

    ## Scan factor
    if params.scan_factor == "half":
        params.scan_factor = 0.5
        params.sl_count = int(iy / 2)
    elif params.scan_factor == "double":
        params.scan_factor = 2
        params.sl_count = iy * 2
    else:
        params.scan_factor = 1
        params.sl_count = iy

    ## Set some shorthand vars and calculate stuff
    params.sxint = int(ix * params.prescale_by)
    params.px = int(ix * params.prescale_by * params.px_aspect)
    params.py = int(iy * params.prescale_by)
    params.ox = int(round((params.oy / iy) * params.px_aspect * ix))


def scale(img: Image.Image, factor: float, strategy: str = "NEAREST"):
    """Scale an image by the given factor.

    Parameters
    ----------
    strategy : {'NEAREST', 'BOX', 'BILINEAR', 'HAMMING', 'BICUBIC', 'LANCZOS'}
    """
    out = ImageOps.scale(img, factor, resample=getattr(Image, strategy))
    return out


def fit(img: Image.Image, new_size: Tuple[int, int], strategy: str = "NEAREST"):
    """Scale an image to fit the new size (as x, y)."""
    out = ImageOps.fit(img, new_size, method=getattr(Image, strategy))
    return out


def scale_horizontal(img: Image.Image, factor: float, strategy: str = "NEAREST"):
    """Scale horizontal only."""
    new_dimensions = (int(factor * img.width), img.height)
    out = img.resize(new_dimensions, resample=getattr(Image, strategy))
    return out


def scale_vertical(img: Image.Image, factor: float, strategy: str = "NEAREST"):
    """Scale vertical only."""
    new_dimensions = (img.width, int(factor * img.height))
    out = img.resize(new_dimensions, resample=getattr(Image, strategy))
    return out


def apply_gamma(img: Image.Image, gamma: float):
    """Apply gamma correction to image."""
    return img.point(lambda i: 255 * ((i / 255) ** gamma))


def gaussian_blur(
    img: Image.Image, h_amount: float, v_amount: Union[float, None] = None, steps=1
):
    for _ in range(steps):
        xy_radius = (h_amount, v_amount)
        img = img.filter(ImageFilter.GaussianBlur(xy_radius))
    return img


def apply_halation(img: Image.Image, radius: float, alpha: float):
    blurred = gaussian_blur(img, h_amount=radius, v_amount=radius, steps=1)
    lightened = ImageChops.lighter(img, blurred)
    return ImageChops.blend(img, lightened, alpha)


def desaturate(img: Image.Image, gamma: float = 1.0):
    if gamma != 1.0:
        img = apply_gamma(img, gamma)
    img = ImageEnhance.Color(img).enhance(0.0)
    if gamma != 1.0:
        img = apply_gamma(img, 1.0 / gamma)
    return img


def create_scanline_img(
    dimensions: Tuple[int, int], scanline_weight: float, scanline_count: int
) -> Image.Image:
    MAX_VAL = 255
    width, height = dimensions
    single_scanline = Image.new("L", (1, height))
    for y in range(height):
        val = math.pow(math.sin(y * math.pi / height), 1 / scanline_weight)
        single_scanline.putpixel((0, y), int(val * MAX_VAL))
    single_scanline = scale_horizontal(single_scanline, factor=width)

    scanlines = Image.new(
        "L", (single_scanline.width, scanline_count * single_scanline.height)
    )
    for y in range(scanline_count):
        scanlines.paste(single_scanline, (0, y * single_scanline.height))
    return scanlines


def create_shadowmask(width, height, input_file, scale_factor=1):
    gamma = 2.2
    with Image.open(input_file) as shadowmask_1x:
        if shadowmask_1x.mode != "RGB":
            shadowmask_1x = shadowmask_1x.convert("RGB")

    shadowmask_1x = apply_gamma(shadowmask_1x, gamma)
    if scale_factor != 1:
        shadowmask_1x = ImageOps.scale(
            shadowmask_1x, scale_factor, resample=Image.LANCZOS
        )

    # shadowmask_1x.save("../debug-steps/TMPshadowmask_1x.png")
    shadowmask = Image.new("RGB", (width, height))
    for y in range(0, height, shadowmask_1x.height):
        for x in range(0, width, shadowmask_1x.width):
            shadowmask.paste(shadowmask_1x, (x, y))

    shadowmask = scale(shadowmask, 2, "BILINEAR")
    shadowmask = scale(shadowmask, 0.5, "BICUBIC")
    shadowmask = apply_gamma(shadowmask, 1 / gamma)
    return shadowmask


@click.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.argument("in_file", type=click.Path(exists=True))
@click.argument("out_file", required=False, type=click.Path(exists=False))
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    help="if set, will write all intermediate image processing steps to files",
)
def main(config_file, in_file, out_file, debug):
    config_file = Path(config_file)
    in_file = Path(in_file)
    if out_file:
        out_file = Path(out_file)
    else:
        out_file = in_file.parent / "{}_{}{}".format(
            in_file.stem, config_file.stem, in_file.suffix
        )
    params = read_config_file(config_file)

    tmpdir = out_file.parent / "debug-steps"
    tmpdir.mkdir(exist_ok=True)

    img = Image.open(in_file)
    if img.mode != "RGB":
        img = img.convert("RGB")
    adjust_params(params, img.width, img.height)

    # ===== Step 01 =====
    click.echo("Step 01")
    img = apply_gamma(img, GAMMA_CORRECTION)
    img = scale_horizontal(img, factor=params.prescale_by, strategy="NEAREST")
    img = scale_horizontal(img, factor=params.px_aspect, strategy="BILINEAR")
    img = scale_vertical(img, factor=params.prescale_by, strategy="NEAREST")
    img = gaussian_blur(
        img,
        params.h_px_blur / 100 * params.prescale_by * params.px_aspect,
        params.v_px_blur / 100 * params.prescale_by,
        steps=1,
    )
    if debug:
        click.echo("    - Saving temp file: step 1 gamma and blur")
        img.save(tmpdir / f"TMPstep01{out_file.suffix}")

    # ===== Step 02 =====
    click.echo("Step 02")
    img = apply_halation(img, params.halation_radius, params.halation_alpha)
    if params.blackpoint:
        img = img.point(lambda val: val + params.blackpoint)
    img = apply_gamma(img, 1.0 / GAMMA_CORRECTION)
    if debug:
        click.echo("    - Saving temp file: step 2 halation and gamma")
        img.save(tmpdir / f"TMPstep02{out_file.suffix}")

    # ===== Step 03 =====
    click.echo("Step 03")
    if params.scanlines_on:
        img_scanlines = create_scanline_img(
            (params.px, int(params.prescale_by / params.scan_factor)),
            params.sl_weight,
            params.sl_count,
        )
        if debug:
            click.echo("    - Saving temp file: scanlines")
            img_scanlines.save(tmpdir / f"TMPscanlines{out_file.suffix}")
        if params.bloom_on:
            img_desaturated = desaturate(img, gamma=GAMMA_CORRECTION).convert("L")  # g

            # create mask where value >= 128
            img_mask = img_desaturated.point(
                lambda val: val >= int(0.55 * params.max) and params.max
            )
            if debug:
                click.echo("    - Saving temp file: scanline mask")
                img_mask.save(tmpdir / f"TMPscanlines-mask{out_file.suffix}")
            img_bloom = ImageMath.eval(
                "b + (m - b) * k * (a - h) / h",
                a=img_desaturated.convert("F"),
                b=img_scanlines.convert("F"),
                k=params.bloom_power,
                m=params.max,
                h=params.half,
            )
            if debug:
                click.echo("    - Saving temp file: bloom")
                img_bloom.convert("L").save(tmpdir / f"TMPbloom-tmp{out_file.suffix}")
            img_scanlines.paste(img_bloom, None, img_mask)
            # img_scanlines.save(tmpdir / f"TMPbloom{out_file.suffix}")

        if params.ovl_alpha > 0:
            shadowmask = create_shadowmask(
                params.px,
                params.py,
                f"_{params.ovl_type}{out_file.suffix}",
                params.ovl_scale,
            )
            if debug:
                click.echo("    - Saving temp file: shadow mask")
                shadowmask.save(tmpdir / f"TMPshadowmask{out_file.suffix}")

            scanline_mult = ImageChops.multiply(img, img_scanlines.convert("RGB"))
            scanline_mult = ImageChops.blend(img, scanline_mult, params.sl_alpha)
            img = ImageChops.multiply(scanline_mult, shadowmask)
            img = ImageChops.blend(scanline_mult, img, params.ovl_alpha)
            img = img.point(lambda val: params.brighten * val)
    if debug:
        click.echo("    - Saving temp file: step 3 (pre-resize)")
        img.save(tmpdir / f"TMPstep03{out_file.suffix}")
    click.echo("Resizing...")
    img = img.resize((int(params.ox), int(params.oy)), resample=Image.LANCZOS)
    click.echo("Saving...")
    img.save(out_file)


if __name__ == "__main__":
    main()
