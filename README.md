# ProteinBinding

An early desktop GUI for our protein-binding project, built with PySide6, Qt Widgets, and 3Dmol.js. The GUI connects to the team's structure parser and HRas mutation scoring functions through `src/adapters/hras.py`.

The layout puts the 3D structure and residue sequence on the left, and predefined contact sites, mutation selection, scores, and PI3K partner amino acids on the right. The default structure is the tracked `reference/hras_project/4EFL.cif`, showing H-Ras chain A.

The screenshot below shows the earlier two-chain demo layout.

![GUI](./example.png)

## Set up the environment

Install [micromamba](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html) first. Run the following commands from the project root, where this README is located.

Use `environment.yml` as the shared environment definition. It includes Python 3.12 and the project's Python dependencies.

Create the environment once:

```bash
micromamba create -n ProteinBinding -f environment.yml -y
```

Activate it before running the project:

```bash
micromamba activate ProteinBinding
```

When adding a package, add it to `environment.yml` and commit that change. Teammates can then update their existing environment with:

```bash
micromamba env update -n ProteinBinding -f environment.yml
```

## Download the local resources

The `resources/` directories are excluded from Git. Download the viewer library after cloning; the command creates the target directory automatically.

Download the pinned 3Dmol.js library:

```bash
curl --fail --location --create-dirs \
  'https://cdn.jsdelivr.net/npm/3dmol@2.5.3/build/3Dmol-min.js' \
  --output src/resources/vendor/3Dmol.min.js
```

The default 4EFL structure is already tracked in the repository. Once the viewer library is downloaded, the GUI runs locally without a server or an internet connection.

## Run

With the `ProteinBinding` environment active, run:

```bash
python src/__main__.py
```

To use another compatible HRas structure and author chain ID:

```bash
python src/__main__.py --structure /path/to/hras.pdb --chain B
```

PDB and mmCIF files, including `.gz`, are supported. The adapter uses the first model and the selected protein chain. It checks that the ten contact-site positions and original amino acids match the backend's HRas table; unrelated or differently numbered structures are not interchangeable with this table.

## Contact sites and predictions

- Contact sites come directly from `CONTACTS` in `src/backend/aa_array.py`: 25, 33, 36, 37, 38, 39, 40, 41, 63, and 64. They are fixed; there is no distance-cutoff control.
- Highlighted sites can be mutated one at a time. Other residues can be selected for viewing, but replacement and calculation are disabled. The presenter and adapter also enforce this restriction.
- The adapter passes the selected mutation, such as `D33A`, to `binding_strength(["D33A"])`. A new request calls the actual backend function rather than looking up a prepared prediction.
- The returned value is a **placeholder rule score**, mutant minus reference. Negative means tighter and positive means weaker under that rule. It is not a calibrated experimental ΔΔG and has no established kcal/mol unit. For example, `D33A` gives approximately `+2.20`.
- The PI3K partner letters come from the same contact table, including repeated partners. The current backend does not supply their coordinates, complete residue identifiers, or distances, so the GUI displays amino-acid identities and counts only. PI3K is not shown as a second chain.

## Project structure

The main files and their responsibilities:

```text
.
├── environment.yml             # Primary environment and dependency definition
├── pyproject.toml              # Ruff configuration
├── README.md
├── reference/
│   └── hras_project/           # Alan's existing example code and structure data
│       ├── 4EFL.cif
│       └── pdb_parser.py
├── src/
│   ├── __main__.py             # Entry point and wiring of concrete implementations
│   ├── contracts.py            # GUI-facing data types and interfaces
│   ├── presenter.py            # User actions, application state, and workflow
│   ├── view.py                 # Qt window and standard widgets
│   ├── viewer.py               # Molecular viewer and Python–JavaScript bridge
│   ├── tasks.py                # Background task execution
│   ├── style.qss               # Qt colors, typography, and widget styles
│   ├── icons/                  # Small, tracked GUI assets
│   ├── viewer_web/
│   │   ├── index.html          # Local page inside QWebEngineView
│   │   └── viewer.js           # 3Dmol rendering and selection events
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── hras.py             # Parser/contact-table mapping and scoring adapter
│   ├── backend/
│   │   ├── structure_parser.py # Team's PDB/mmCIF parser
│   │   └── aa_array.py         # Team's fixed contact sites and placeholder score
│   └── resources/
│       └── vendor/
│           └── 3Dmol.min.js    # Downloaded locally; excluded from Git
└── tests/
    ├── functional/            # unittest: single-chain 3D, selection, and scoring flow
    └── unit/                  # unittest: adapter and presenter behavior without Qt
```

## Tests and code checks

Tests use Python's standard-library **`unittest`**. They cover structure/contact mapping, score integration, mutation restrictions, stale task results, and the real Qt/WebEngine workflow. Run commands from the project root with the environment active.

Adapter and presenter tests, without starting Qt or downloading the viewer resources:

```bash
PYTHONPATH=src python -m unittest discover -s tests/unit -v
```

GUI checks require a desktop session and the downloaded 3Dmol.js library:

```bash
PYTHONPATH=src:. python -m unittest discover -s tests/functional -v
```

## Team to-do list

- [ ] Natalie: Data extraction
- [ ] Julian: GUI
- [ ] Alan: Further data manipulation

## Message board

**Julian**: This is the initial structure I've put together to get us started. **I am open to any change**, so please feel free to suggest a different layout or approach if it works better for the team. Please put your backend code in **`src/backend/`** and design the functions however makes sense for your work. Once your code is ready, I'll read through it and write the adapters to connect it to the GUI. A short usage example showing the inputs and outputs would be really helpful when we get to that point. Thanks! 
