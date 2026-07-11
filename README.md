# 2d-gastruloid-analysis

Analysis of human 2D gastruloid data

## Data

Datasets used for notebooks have been uploaded to zenodo and made public, and the code for downloading data has been added to each notebook.

## Setup

### Install uv

If uv is not already available:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Create the virtual environment

```bash
# run this at the root of this project
uv sync
```

### Activate venv

```bash
./activate-venv
# or
source activate-venv
```

### Register an IPython kernel *(optional)*

```bash
uv run ipython kernel install --name 'any name you want' --user
```

### Add packages

```bash
uv add <any package you want>
```

## Uninstalling uv

```bash
uv cache clean
rm -r "$(uv python dir)"
rm -r "$(uv tool dir)"
rm ~/.local/bin/uv ~/.local/bin/uvx
```
