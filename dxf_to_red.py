#!/usr/bin/env python3
"""
Take an OpenSCAD (.scad) or DXF (.dxf) file, and produce a DXF where every
entity is colored red (ACI color 1) -- for laser cutters that use color to
decide cut vs. raster.

Usage:
    python3 dxf_to_red.py /path/to/file.scad
    python3 dxf_to_red.py /path/to/file.dxf

Output is written next to the input file as "<name>_red.dxf".
"""

import sys
import subprocess
import shutil
from pathlib import Path

import ezdxf

RED_ACI = 1  # AutoCAD Color Index for pure red (255, 0, 0)


def export_scad_to_dxf(scad_path: Path) -> Path:
    """Run openscad to export a .scad file to .dxf, return the dxf path."""
    if shutil.which("openscad") is None:
        sys.exit(
            "Error: 'openscad' CLI not found on PATH. Either install it, "
            "or export the DXF yourself and pass that .dxf file instead."
        )

    dxf_path = scad_path.with_suffix(".dxf")
    cmd = ["openscad", "-o", str(dxf_path), str(scad_path)]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        sys.exit(f"OpenSCAD export failed:\n{result.stderr}")

    if not dxf_path.exists():
        sys.exit("OpenSCAD did not produce a DXF file (check your .scad is 2D).")

    return dxf_path


def recolor_dxf_to_red(dxf_path: Path) -> Path:
    """Set every entity's color to red, and save as <name>_red.dxf."""
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    count = 0
    for entity in msp:
        entity.dxf.color = RED_ACI
        count += 1

    # Also color layer "0" red, in case the software reads by-layer instead
    # of by-entity.
    if "0" in doc.layers:
        doc.layers.get("0").color = RED_ACI

    out_path = dxf_path.with_name(dxf_path.stem + "_red.dxf")
    doc.saveas(str(out_path))
    print(f"Recolored {count} entities to red. Saved: {out_path}")
    return out_path


def main():
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python3 {sys.argv[0]} <path/to/file.scad|.dxf>")

    input_path = Path(sys.argv[1]).expanduser().resolve()
    if not input_path.exists():
        sys.exit(f"File not found: {input_path}")

    suffix = input_path.suffix.lower()

    if suffix == ".scad":
        dxf_path = export_scad_to_dxf(input_path)
    elif suffix == ".dxf":
        dxf_path = input_path
    else:
        sys.exit(f"Unsupported file type '{suffix}'. Pass a .scad or .dxf file.")

    recolor_dxf_to_red(dxf_path)


if __name__ == "__main__":
    main()
    