# FFmpeg CRT Transform

Script to simulate CRT monitors and flat-panel displays from an input image.

## Contents

<!-- vim-markdown-toc GFM -->

  - [About](#about)
  - [Requirements](#requirements)
  - [Quickstart](#quickstart)
  - [Examples](#examples)
    - [CRT television simulation](#crt-television-simulation)
    - [NTSC simulation](#ntsc-simulation)
- [FFmpeg CRT Transform (original README)](#ffmpeg-crt-transform-original-readme)
  - [Usage and Configuration](#usage-and-configuration)
  - [Tips](#tips)
  - [Write-ups, videos, sample images](#write-ups-videos-sample-images)

<!-- vim-markdown-toc -->

## About

This is the [de-mux](https://github.com/de-mux/FFmpeg-CRT-transform) fork of the
[vegardsjo fork](https://github.com/vegardsjo/FFmpeg-CRT-transform) fork of
[FFmpeg-CRT-transform](https://github.com/viler-int10h/FFmpeg-CRT-transform/).

It contains the following additions:

- [`ffcrt-pillow.py`](./ffcrt-pillow.py) - reimplementation using Python
  [Pillow](https://python-pillow.org/) library.

  **Note** not all original functionality has been implemented at this time. The
  script will warn you if you use any configuration parameters that are not
  supported.

- [`ntsc.py`](./ntsc.py) - an NTSC simulation script that you can use prior to
  running the CRT simulator, originally from
  [zhuker/ntsc](https://github.com/zhuker/ntsc) (licensed under
  [Apache 2.0](./ntsc.LICENSE)). Note that it requires the included
  `ringPattern.npy` compiled script to run.

## Requirements

- Python 3.9 or newer
- It's recommended to always have a Python
  [virtual environment](https://docs.python.org/3/library/venv.html) active when
  doing anything with Python

## Quickstart

- Activate your Python virtual environment
- Install requirements:

  ```bash
  pip install -r requirements.txt
  ```

- See [Examples](#Examples) for usage.

## Examples

### CRT television simulation

From a terminal shell:

```bash
python ffcrt-pillow.py presets/color-PAL-TV-2.cfg <input-image.jpg> <output-image.jpg>
```

### NTSC simulation

From Python(assuming your script is in the repo's root directory):

```python
import ntsc
ntsc.ntsc_realistic("/path/to/input-image.png", "/path/to/output-image.png", prescale=4)
```

---

_... begin original readme file ..._

---

# FFmpeg CRT Transform (original README)

Windows batch script for a configurable simulation of CRT monitors (and some
older flat-panel displays too), given an input image/video.

Requires a _git-master_ build of FFmpeg from **2021-01-27** or newer, due to a
couple of bugfixes and new features.

See <https://github.com/viler-int10h/FFmpeg-CRT-transform/> for the latest
version.

## Usage and Configuration

Syntax: `ffcrt <config_file> <input_file> [output_file]`

- `input_file` must be a valid image or video. Assumed to be 24-bit RGB (8
  bits/channel).

- If `output_file` is omitted, the output will be named
  "(input*file)*(config_file).(input_ext)".

- **How to configure**: all settings/parameters are commented in the sample
  configuration files, which you can find in the "presets" subdir.

  **NOTE**: the included presets aren't guaranteed to accurately simulate any
  particular monitor model, but they may give you a good starting point!

## Tips

- Input is expected to have the same resolution (=_storage_ aspect ratio, SAR)
  of the video mode you are simulating, including overscan if any.
- The aspect ratio **of the simulated screen** (=_display_ aspect ratio, DAR) is
  not set directly, but depends on the SAR and on the _pixel_ aspect ratio
  (PAR): DAR=SAR×PAR. The PAR is set with the `PX_ASPECT` parameter.
- The aspect ratio **of your final output** is set separately with the `OASPECT`
  parameter. If it's different from the above, the simulated screen will be
  scaled and padded as necessary while maintaining its aspect ratio, so you can
  have e.g. a 4:3 screen centered in a 16:9 video.

- Processing speed and quality is determined by the `PRESCALE_BY` setting. This
  also affects FFmpeg's RAM consumption, so if you get memory allocation errors
  try a lower factor.
- _Most_ of the processing chain uses a color depth of 8 bits/component by
  default. Setting `16BPC_PROCESSING` to `yes` will make all the intermediate
  steps use 16 instead. That makes the process twice as slow and RAM-hungry, but
  if your settings are giving you prominent banding artifacts and such, try
  going 16-bit.
- By default the output colorspace is 24-bit RGB (8 bits/component), but you can
  change that by setting `OFORMAT` to 1: for videos, this will output YUV 4:4:4
  at 10 bits/component. For images, you'll get 48-bit RGB (16 bits/component),
  which works with .png or .tif for instance.

  (Of course, to get the most out of this, you'll want 16bpc processing as
  mentioned above)

- In general, speed is the weakest link in this whole thing, so you may want to
  test your config file on a still .png image (or on a few seconds of video)
  first, tweak things to your liking, and tackle longer videos only after you've
  finalized your settings.

## Write-ups, videos, sample images

1. **Color CRTs:**
   https://int10h.org/blog/2021/01/simulating-crt-monitors-ffmpeg-pt-1-color/<br><br>
   <a href="https://int10h.org/blog/2021/01/simulating-crt-monitors-ffmpeg-pt-1-color/"><img src="../images/r01s.png?raw=true" height="480">
   </a>

2. **Monochrome CRTs:**
   https://int10h.org/blog/2021/02/simulating-crt-monitors-ffmpeg-pt-2-monochrome/<br><br>
   <a href="https://int10h.org/blog/2021/02/simulating-crt-monitors-ffmpeg-pt-2-monochrome/"><img src="../images/r02s.png?raw=true" height="480">
   </a>

3. **Flat-Panel Displays:**
   https://int10h.org/blog/2021/03/simulating-non-crt-monitors-ffmpeg-flat-panels/<br><br>
   <a href="https://int10h.org/blog/2021/03/simulating-non-crt-monitors-ffmpeg-flat-panels/"><img src="../images/r03s.png?raw=true" height="480">
   </a>
