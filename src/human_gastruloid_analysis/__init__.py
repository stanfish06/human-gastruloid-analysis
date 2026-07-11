"""
==============
Python helpers
==============
"""

from __future__ import annotations

import tarfile
import urllib.request
from pathlib import Path

import yaml
from tqdm.auto import tqdm

from .knn import weighted_knn_trainer, weighted_knn_transfer
from .models import model_table

__all__ = [
    "model_table",
    "download_data",
    "list_data",
    "weighted_knn_trainer",
    "weighted_knn_transfer",
]

#: Zenodo record id that hosts the datasets. Set this once after uploading, e.g.
#: ``import human_gastruloid_analysis as hga; hga.ZENODO_RECORD_ID = "1234567"``.
#: Alternatively pass ``record_id=...`` to :func:`download_data`, or add a
#: ``url``/``record_id`` field to individual entries in ``data_registry.yaml``.
ZENODO_RECORD_ID: str | None = None

#: Template for a direct file download from a public Zenodo record.
_ZENODO_FILE_URL = "https://zenodo.org/records/{record_id}/files/{filename}?download=1"

#: Location of the dataset registry shipped with the package.
_REGISTRY_PATH = Path(__file__).parent / "data_registry.yaml"

#: Project root, derived from this file's location (``src/<pkg>/__init__.py``).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

#: Default download directory: the project's root ``data/`` folder. Using an
#: absolute path here keeps downloads in one place regardless of the working
#: directory (e.g. when run from ``notebooks/``).
DEFAULT_DATA_DIR = _PROJECT_ROOT / "data"


def _load_registry(registry_path: str | Path | None = None) -> dict[str, dict]:
    """Read and parse the dataset registry.

    Parameters
    ----------
    registry_path : str or pathlib.Path, optional
        Path to the registry YAML. Defaults to the ``data_registry.yaml``
        shipped inside the package.

    Returns
    -------
    dict of str to dict
        Mapping of dataset name to its registry entry.
    """
    path = Path(registry_path) if registry_path is not None else _REGISTRY_PATH
    with open(path) as handle:
        return yaml.safe_load(handle)


def _zenodo_url(record_id: str | None, filename: str) -> str:
    """Build a direct Zenodo download URL for a single file.

    Parameters
    ----------
    record_id : str or None
        Zenodo record id the file belongs to.
    filename : str
        Name of the file (or archive) stored in the record.

    Returns
    -------
    str
        Direct download URL.

    Raises
    ------
    ValueError
        If ``record_id`` is ``None``.
    """
    if record_id is None:
        raise ValueError(
            "No Zenodo record id is set, so the download URL cannot be built. "
            "Set human_gastruloid_analysis.ZENODO_RECORD_ID, pass record_id=... "
            "to download_data(), or add a 'url'/'record_id' field to the entry "
            "in data_registry.yaml."
        )
    return _ZENODO_FILE_URL.format(record_id=record_id, filename=filename)


def _download_file(url: str, out_path: str | Path, *, overwrite: bool = False) -> Path:
    """Stream a single file to disk, showing a progress bar.

    Parameters
    ----------
    url : str
        Source URL to download from.
    out_path : str or pathlib.Path
        Destination path for the downloaded file.
    overwrite : bool, default False
        If ``False`` and ``out_path`` already exists, the download is skipped.

    Returns
    -------
    pathlib.Path
        Path to the downloaded (or already present) file.
    """
    out_path = Path(out_path)
    if out_path.exists() and not overwrite:
        print(f"  ✓ {out_path.name} already present, skipping")
        return out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(out_path.name + ".part")
    request = urllib.request.Request(
        url, headers={"User-Agent": "human-gastruloid-analysis"}
    )
    with urllib.request.urlopen(request) as response:  # noqa: S310 (trusted URLs)
        total = int(response.headers.get("Content-Length") or 0) or None
        with (
            open(tmp_path, "wb") as handle,
            tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=out_path.name,
            ) as bar,
        ):
            for chunk in iter(lambda: response.read(1 << 20), b""):
                handle.write(chunk)
                bar.update(len(chunk))
    tmp_path.replace(out_path)
    return out_path


def _extract_archive(archive_path: str | Path, dest: str | Path) -> None:
    """Extract a ``.tar.gz`` archive into ``dest``.

    Parameters
    ----------
    archive_path : str or pathlib.Path
        Path to the gzip-compressed tar archive.
    dest : str or pathlib.Path
        Directory to extract into. The archive is expected to contain the
        dataset's ``subdir`` folder, so files end up in ``dest/<subdir>/``.
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(dest, filter="data")


def _entry_url(
    entry: dict, filename: str, record_id: str | None, file_entry: dict | None = None
) -> str:
    """Resolve the download URL for a file, honouring registry overrides.

    Resolution order: an explicit ``url`` on the file entry, then on the dataset
    entry, then a Zenodo URL built from the first available record id
    (file entry, dataset entry, ``record_id`` argument, module default).
    """
    if file_entry is not None and file_entry.get("url"):
        return file_entry["url"]
    if entry.get("url"):
        return entry["url"]
    resolved_id = (
        (file_entry or {}).get("record_id")
        or entry.get("record_id")
        or record_id
        or ZENODO_RECORD_ID
    )
    return _zenodo_url(resolved_id, filename)


def download_data(
    name: str,
    dest: str | Path = DEFAULT_DATA_DIR,
    *,
    record_id: str | None = None,
    overwrite: bool = False,
    keep_archive: bool = False,
    registry_path: str | Path | None = None,
) -> Path | list[Path]:
    """Download a dataset (or all datasets) listed in the registry.

    Datasets are described in ``data_registry.yaml``. A dataset whose
    ``need_unzip`` flag is ``true`` is stored on Zenodo as a single
    ``<subdir>.tar.gz`` archive that is downloaded and extracted into
    ``dest/<subdir>/``. A dataset with ``need_unzip: false`` has each file in
    its ``checklist`` downloaded individually into ``dest/<subdir>/`` without
    extraction.

    Parameters
    ----------
    name : str
        Dataset key from the registry (e.g. ``"IH-2025-nature"``), or the
        special value ``"all"`` to download every dataset.
    dest : str or pathlib.Path, optional
        Base directory downloads are written to. Defaults to the project's
        root ``data/`` folder (:data:`DEFAULT_DATA_DIR`). Each dataset lands in
        its own ``subdir`` beneath this directory.
    record_id : str, optional
        Zenodo record id to download from. Overrides :data:`ZENODO_RECORD_ID`
        but is itself overridden by any ``record_id``/``url`` set on a registry
        entry.
    overwrite : bool, default False
        Re-download even if the target files/directory already exist.
    keep_archive : bool, default False
        For ``need_unzip`` datasets, keep the downloaded ``.tar.gz`` after a
        successful extraction instead of deleting it.
    registry_path : str or pathlib.Path, optional
        Alternative registry file. Defaults to the packaged registry.

    Returns
    -------
    pathlib.Path or list of pathlib.Path
        The dataset directory that was populated, or a list of such
        directories when ``name == "all"``.

    Raises
    ------
    KeyError
        If ``name`` is not a dataset in the registry.
    ValueError
        If a download URL cannot be resolved (no ``url`` and no Zenodo record id).

    Examples
    --------
    >>> import human_gastruloid_analysis as hga
    >>> hga.ZENODO_RECORD_ID = "1234567"  # doctest: +SKIP
    >>> hga.download_data("IH-2025-nature")  # doctest: +SKIP
    PosixPath('data/IH-2025-nature-data')
    """
    registry = _load_registry(registry_path)

    if name == "all":
        return [
            _download_one(
                key,
                registry[key],
                dest,
                record_id=record_id,
                overwrite=overwrite,
                keep_archive=keep_archive,
            )
            for key in registry
        ]

    if name not in registry:
        raise KeyError(
            f"{name!r} is not in the registry. Available datasets: {list(registry)}"
        )

    return _download_one(
        name,
        registry[name],
        dest,
        record_id=record_id,
        overwrite=overwrite,
        keep_archive=keep_archive,
    )


def _download_one(
    name: str,
    entry: dict,
    dest: str | Path,
    *,
    record_id: str | None,
    overwrite: bool,
    keep_archive: bool,
) -> Path:
    """Download a single registry entry. See :func:`download_data`."""
    dest = Path(dest)
    subdir = entry.get("subdir", name)
    target_dir = dest / subdir
    checklist = entry.get("checklist", []) or []

    if entry.get("need_unzip"):
        if target_dir.exists() and any(target_dir.iterdir()) and not overwrite:
            print(f"{name}: already present at {target_dir}, skipping")
            return target_dir
        archive = entry.get("archive", f"{subdir}.tar.gz")
        url = _entry_url(entry, archive, record_id)
        print(f"{name}: downloading {archive}")
        archive_path = _download_file(url, dest / archive, overwrite=overwrite)
        print(f"{name}: extracting into {dest}/")
        _extract_archive(archive_path, dest)
        if not keep_archive:
            archive_path.unlink(missing_ok=True)
    else:
        print(f"{name}: downloading {len(checklist)} file(s) into {target_dir}/")
        for item in checklist:
            filename = item["file"]
            url = _entry_url(entry, filename, record_id, file_entry=item)
            _download_file(url, target_dir / filename, overwrite=overwrite)

    print(f"{name}: done -> {target_dir}")
    return target_dir


def list_data(
    name: str | None = None, *, registry_path: str | Path | None = None
) -> None:
    """Print the datasets in the registry and their per-file descriptions.

    Reads ``data_registry.yaml`` and prints, for every dataset, its metadata
    (paper link, source, target subdirectory) followed by each file and its
    description. Multi-line descriptions are joined with newlines.

    Parameters
    ----------
    name : str, optional
        Show only this dataset. If ``None`` (default), all datasets are shown.
    registry_path : str or pathlib.Path, optional
        Alternative registry file. Defaults to the packaged registry.

    Returns
    -------
    None
        The listing is written to standard output.

    Raises
    ------
    KeyError
        If ``name`` is given but not found in the registry.
    """
    registry = _load_registry(registry_path)

    if name is not None:
        if name not in registry:
            raise KeyError(
                f"{name!r} is not in the registry. Available datasets: {list(registry)}"
            )
        registry = {name: registry[name]}

    blocks: list[str] = []
    for ds_name, entry in registry.items():
        checklist = entry.get("checklist", []) or []
        unzip = "needs unzip" if entry.get("need_unzip") else "no unzip"
        header = f"{ds_name}  ({len(checklist)} file(s), {unzip})"

        lines = [header, "=" * len(header)]
        if entry.get("link"):
            lines.append(f"paper : {entry['link']}")
        if entry.get("source"):
            lines.append(f"source: {entry['source']}")
        lines.append(f"subdir: {entry.get('subdir', '')}")
        lines.append("")

        for index, item in enumerate(checklist, start=1):
            description = item.get("description") or []
            if isinstance(description, str):
                description = [description]
            lines.append(f"  {index}. {item['file']}")
            lines.extend(f"       {line}" for line in description)

        blocks.append("\n".join(lines))

    print("\n\n".join(blocks))
