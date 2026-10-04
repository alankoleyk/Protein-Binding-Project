# ProteinBinding

An early desktop GUI for our protein-binding project, built with PySide6, Qt Widgets, and 3Dmol.js. It currently runs with a small demo adapter so we can develop the GUI before the scientific backend is ready.

The single-page layout puts the 3D structure and residue sequence on the left, and interface settings, mutation selection, demo predictions, and nearby residues on the right.

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

The `resources/` directories are excluded from Git. Run both commands after cloning; they create the target directories automatically.

Download the pinned 3Dmol.js library:

```bash
curl --fail --location --create-dirs \
  'https://cdn.jsdelivr.net/npm/3dmol@2.5.3/build/3Dmol-min.js' \
  --output src/resources/vendor/3Dmol.min.js
```

Download the demo structure, [RCSB 1BRS](https://www.rcsb.org/structure/1BRS):

```bash
curl --fail --location --create-dirs \
  'https://files.rcsb.org/download/1BRS.pdb' \
  --output src/resources/demo/1brs.pdb
```

These files are required to launch the GUI. Once downloaded, the viewer runs locally without a server or an internet connection. The optional **View in PDB** link opens the RCSB website in your browser. See the [3Dmol.js documentation](https://3dmol.org/doc/) for its API and license information.

## Run

With the `ProteinBinding` environment active, run:

```bash
python src/__main__.py
```

Try dragging the structure to rotate, scrolling to zoom, or clicking a residue in the 3D view or sequence. The camera buttons provide auto-rotation, zoom, focus, and reset. You can also switch chains and cartoon/stick/surface representations.

Start with **chain D, residue 39 → Alanine (A)**, then click **Preview mutation effect**. Change the replacement to Asparagine (N) for another prepared example. Changing a prediction input clears the old result. Mutations without a prepared fixture show **No demo value**.

The structure and precomputed inter-chain distances are real; **all predicted and experimental affinity values shown in this shell are invented**. Selecting a mutation does not alter the coordinates or model a mutant structure. There is no training or scientific inference backend yet.

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
│   │   ├── demo.py             # Temporary backend with fixed prediction fixtures
│   │   └── demo_residues.json  # Precomputed geometry for the single demo structure
│   ├── backend/               # Backend implementation goes here
│   └── resources/
│       ├── demo/
│       │   └── 1brs.pdb        # Downloaded locally; excluded from Git
│       └── vendor/
│           └── 3Dmol.min.js    # Downloaded locally; excluded from Git
└── tests/
    ├── functional/            # unittest: real Qt/WebEngine and worker integration
    └── unit/                  # unittest: presenter behavior without Qt
```

The GUI uses a lightweight MVP structure:

- **View** (`view.py`): displays state and emits user actions. It does not import a backend or the presenter.
- **Presenter** (`presenter.py`): manages selection, input changes, and prediction state. It uses ordinary Python data classes and protocols, with no Qt imports.
- **Adapter** (`adapters/demo.py` for now): supplies data through the GUI-facing `BackendPort` in `contracts.py`.
- **Viewer** (`viewer.py` + `viewer_web/`): contains the Python–JavaScript boundary. JavaScript renders molecules and reports clicks; it does not calculate affinity.
- **Task runner** (`tasks.py`): runs predictions on a worker and delivers results on the GUI thread. Results from outdated inputs are ignored by the presenter.

`__main__.py` connects these pieces. To connect a real backend later, add an adapter in `src/adapters/` that wraps the functions in `src/backend/`, then replace `DemoBackend()` at the entry point. The GUI-facing methods are currently `load_structure()`, `find_interface(structure, cutoff)`, and `predict(request)`; **these do not prescribe the backend team's API**. The real backend does not need to import Qt or these GUI contracts. The current structure loader expects a local PDB file.

Loading this small demo and filtering its precomputed contacts are synchronous; predictions use the worker. When actual parsing or interface calculations become expensive, those calls can use the same task runner too.

## Tests and code checks

Tests use Python's standard-library **`unittest`**; no separate test framework is required. The tests cover presenter behavior, GUI signal wiring, layout stability, and worker callbacks. Run commands from the project root with the environment active.

Fast presenter tests, without starting Qt or downloading the viewer resources:

```bash
PYTHONPATH=src python -m unittest discover -s tests/unit -v
```

GUI integration tests, after downloading both resources:

```bash
PYTHONPATH=src python -m unittest discover -s tests/functional -v
```

The GUI tests briefly open real windows and require a desktop session with working WebGL. Leave those windows alone while the tests run. On macOS, use the normal display driver: Qt's offscreen driver can lose its WebGL context.

```bash
python -m ruff check src tests
python -m ruff format --check src tests
```

## Demo data notes

The demo uses chains A (barnase) and D (barstar) from 1BRS. `demo_residues.json` contains 195 resolved residues and the minimum heavy-atom distance for partner residues within 8 Å, rounded to three decimals. It was copied from the earlier `project/gpt` reference prototype, where `scripts/prepare-demo.py` generates it. The slider filters those stored distances; it is not running a new structural analysis.

The barstar in 1BRS has a C40A/C82A background, so these coordinates should not be assumed to be a universal wild-type reference when matching experimental mutation data. The display uses ΔΔG = ΔG(mutant) − ΔG(reference), with positive values meaning weaker binding.

Structure credit: Buckle, Schreiber & Fersht (1994), [RCSB 1BRS](https://www.rcsb.org/structure/1BRS). The GUI shell was developed with Codex assistance; scientific backend implementation and validation remain team work.

## Team to-do list

- [ ] Natalie: Data extraction
- [ ] Julian: GUI
- [ ] Alan: Further data manipulation

## Message board

**Julian**: This is the initial structure I've put together to get us started. **I am open to any change**, so please feel free to suggest a different layout or approach if it works better for the team. Please put your backend code in **`src/backend/`** and design the functions however makes sense for your work. Once your code is ready, I'll read through it and write the adapters to connect it to the GUI. A short usage example showing the inputs and outputs would be really helpful when we get to that point. Thanks! 
