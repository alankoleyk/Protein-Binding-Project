# ProteinBinding

This is an early project skeleton. Most modules are still placeholders. The current entry point only checks that the required Python packages can be imported and shows a confirmation dialog.

## Set up the environment

Install [micromamba](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html) first. Run the following commands from the project root, where this README is located.

Install the recorded development package versions:

```bash
python -m pip install -r requirements-dev.txt
```
When returning to the project later, activate the existing environment before running Python. There is no need to recreate it each time.

If any new packages are installed in the active environment, refresh `requirements-dev.txt` with `python -m pip freeze > requirements-dev.txt` (replace any local `file://` entries with `package==version`), update `environment.yml` to match, and commit both files so we can rerun the install command above.

## Download the 3D viewer library

The `resources/` directories are excluded from Git, so download this library after cloning. This command creates the target directory and downloads a fixed version of 3Dmol.js:

```bash
curl --fail --location --create-dirs \
  'https://cdn.jsdelivr.net/npm/3dmol@2.5.3/build/3Dmol-min.js' \
  --output src/resources/vendor/3Dmol.min.js
```

The library will be used by the future molecular viewer. It is not needed by the current environment-check dialog. See the [3Dmol.js documentation](https://3dmol.org/doc/) for its API and license information.

## Run

With the `ProteinBinding` environment active, run:

```bash
python src/__main__.py
```

If the imports succeed, a dialog displays **“Environment OK!”**. It checks Qt Widgets, WebEngine, WebChannel, and the scientific Python dependencies. This does not yet test actual 3D rendering.

## Project structure

The comments below describe the intended responsibilities of the placeholder modules.

```text
.
├── environment.yml             # micromamba environment definition
├── requirements-dev.txt        # Recorded Python package versions
├── README.md
├── reference/
│   └── hras_project/           # Alan's existing example code and structure data
│       ├── 4EFL.cif
│       └── pdb_parser.py
├── src/
│   ├── __main__.py             # Entry point; currently an environment check
│   ├── contracts.py            # GUI-facing data types and interfaces
│   ├── presenter.py            # User actions, application state, and workflow
│   ├── view.py                 # Qt window and standard widgets
│   ├── viewer.py               # Molecular viewer and Python–JavaScript bridge
│   ├── tasks.py                # Background task execution
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── demo.py             # Planned temporary backend for GUI development
│   ├── backend/               # Backend implementation goes here
│   └── resources/
│       └── vendor/
│           └── 3Dmol.min.js    # Downloaded locally; excluded from Git
└── tests/
    ├── functional/            # Tests of complete workflows
    └── unit/                  # Tests of individual functions and components
```

The GUI will follow a lightweight MVP structure: the **View** displays information, the **Presenter** coordinates actions, and the backend handles the scientific work. Adapters translate between the GUI's internal interfaces and the backend's API. The test directories are reserved for future tests.

## Team to-do list

- [ ] Natalie: Data extraction
- [ ] Julian: GUI
- [ ] Alan: Further data manipulation

## Message board

**Julian**: This is the initial structure I've put together to get us started. **I am open to any change**, so please feel free to suggest a different layout or approach if it works better for the team. Please put your backend code in **`src/backend/`** and design the functions however makes sense for your work. Once your code is ready, I'll read through it and write the adapters to connect it to the GUI. A short usage example showing the inputs and outputs would be really helpful when we get to that point.
