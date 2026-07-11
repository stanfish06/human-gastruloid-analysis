# 2d-gastruloid-analysis

Analysis of human 2D gastruloid data

## Data

All datasets are hosted on [Zenodo record 21313315](https://zenodo.org/records/21313315) (DOI [10.5281/zenodo.21313315](https://doi.org/10.5281/zenodo.21313315)). After the setup below, list and download them from Python — files are saved to the root `data/` folder:

```python
from human_gastruloid_analysis import list_data, download_data

list_data()                      # datasets and descriptions
download_data("IH-2025-nature")  # download one dataset
download_data("all")             # or download everything
```

See [notebooks/data_tour.ipynb](notebooks/data_tour.ipynb) for a guided tour, and [notebooks/](notebooks/README.md) for the analysis pipelines.

For uncovered datasets, check [src/human_gastruloid_analysis/data_registry.yaml](src/human_gastruloid_analysis/data_registry.yaml) for descriptions.

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
uv run ipython kernel install --name 'any name (select later inside jupyterlab or vscode)' --user
```

### Add packages

```bash
uv add <any package (separated by space)>
```

## Uninstalling uv

```bash
uv cache clean
rm -r "$(uv python dir)"
rm -r "$(uv tool dir)"
rm ~/.local/bin/uv ~/.local/bin/uvx
```
