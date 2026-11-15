#!/usr/bin/env python3
"""Build the static GitHub Pages artifact, including clean URL aliases."""

from pathlib import Path
import shutil

try:
    from .site_routes import ROUTES
except ImportError:  # Running as ``python3 tools/build_site.py``.
    from site_routes import ROUTES

ROOT = Path(__file__).resolve().parents[1]


def build_site(destination):
    """Copy the site into an empty directory; no source files are changed."""
    destination = Path(destination)
    if destination.is_symlink():
        raise ValueError("The build destination must not be a symlink")
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ValueError(f"The build destination must be empty: {destination}")

    for name in ("index.html", "styles.css", "script.js", ".nojekyll"):
        shutil.copy2(ROOT / name, destination / name)
    for name in ("assets", "projects", "journals"):
        shutil.copytree(ROOT / name, destination / name)

    # GitHub Pages resolves e.g. /главная to главная.html without a redirect.
    # Original paths remain in the artifact for existing bookmarks.
    for route, source in ROUTES.items():
        alias = destination / (route.lstrip("/") + ".html")
        alias.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / source, alias)


if __name__ == "__main__":
    output = ROOT / "_site"
    if output.is_symlink():
        raise SystemExit("Refusing to replace a symlink at _site")
    if output.exists():
        shutil.rmtree(output)
    build_site(output)
    print(f"Built GitHub Pages artifact in {output}")
