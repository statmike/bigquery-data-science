# `docs/assets/` — Static Documentation, Social Preview & PyPI Mermaid Fallback Assets

This directory holds static visual assets used by the GitHub repository social preview card, `README.md`, and the PyPI package description (`hatch-fancy-pypi-readme` swaps `README.md`'s ` ```mermaid ` block to the pre-rendered PNG at build time because `pypi.org` does not execute Mermaid JS).

## Directory Map

| File | Responsibility |
| :--- | :--- |
| [`README.md`](./README.md) | Directory map and regeneration instructions for static visual assets. |
| [`social_card.html`](./social_card.html) / [`social_card.png`](./social_card.png) | `1280×640` repository social preview card using the four-class palette (`data`, `config`, `route`, `compute`). |
| [`readme_architecture.html`](./readme_architecture.html) / [`readme_architecture.png`](./readme_architecture.png) | `1280×490` PyPI fallback PNG for the front-door architecture diagram in `README.md`. |

## Regenerating PNG Assets

From the repository root:

```bash
DIR="$(pwd)/docs/assets"
google-chrome --headless=new --disable-gpu --hide-scrollbars --window-size=1280,640 --virtual-time-budget=8000 --screenshot="$DIR/social_card.png" "file://$DIR/social_card.html"
google-chrome --headless=new --disable-gpu --hide-scrollbars --window-size=1280,490 --virtual-time-budget=8000 --screenshot="$DIR/readme_architecture.png" "file://$DIR/readme_architecture.html"
```
