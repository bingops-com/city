"""Render recorded canvas geometry through the SVG export, without a browser."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
subprocess.run(["node", str(root / "scripts/render_prototype_map.cjs")], cwd=root, check=True)
