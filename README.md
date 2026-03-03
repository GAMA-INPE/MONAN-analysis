# MONAN-analysis

Project to centralize code for analyses of simulations with the MONAN model.

## Structure
```
monan_analysis/
├── README.md             
├── pyproject.toml        # makes packages inside src/ installable
├── requirements.txt      # lists libraries needed to run repo
├── .gitignore            # lists files to be ignored by git
├── src/                  # source code (installable packages)
│   └── monan_analysis/   # namespace for monan_analysis package
│       ├── __init__.py   # python looks for this file when importing modules
│       ├── utils.py      # reusable general-purpose routines
│       ├── io.py         # reusable routines for reading input and saving output
│       ├── plots.py      # reusable routines for plotting
│       └── stats.py      # reusable routines for calculating statistics
├── analyses/             # ready-to-use analysis code
│   ├── analysis1/
│   │   ├── run1.py        # exemplary main script for analysis1
│   │   └── aux1.py        # exemplary auxiliary script for analysis1
│   └── analysis2/
│       ├── run2.py        # exemplary main script for analysis2
│       └── aux2.py        # exemplary auxiliary script for analysis2
└── exploratory/          # exploratory (preliminary) scripts
```
____________

## Installation guide

### 1. Clone the repository

```
git clone https://github.com/GAMA-INPE/MONAN-analysis.git
cd MONAN-analysis
```

### 2. Set up conda environment

2.1) If using an HPC system, load Anaconda (or other conda)  module
```
module load anaconda
```
2.2) Create conda environment to install project packages
```
conda create -n gama
```
2.3) Activate conda environment
```
conda activate gama
```
2.4) Install python inside that conda environment
```
conda install python=3.12
```
2.5) Make sure python is installed in the conda env
```
which python
```
If the above points to your recently created conda environment, proceed to step 3.

### 3. Install project-specific dependencies
All project-specific dependencies (external and internal packages under `src/`) are listed in `requirements.txt`. Depending on whether you have the external dependencies already installed, you can follow two options: 

a) If you do not yet have the external dependencies, you can install those dependencies plus the internal project packages by running
```
python -m pip install -r requirements.txt
```

b) If you already have the needed external dependencies and want to install only the internal project packages under `src/`, you can do this by running
```
python -m pip install -e .
```
inside your conda environment.

After installation by option a) or b), you should be able to import in particular internal modules from the packages under `src/` in your analysis scripts. You can test this by running from the project's root
```
python exploratory/import_test/example_analysis.py
```
If the internal packages have been correctly installed, this test should return
```
this is a function imported from the utils.py module.
this is a function imported from the io.py module.
this is a function imported from the plots.py module.
this is a function imported from the stats.py module.
```

____________

## Quick user & developer guide
The core idea behind this project is that analysis scripts, although developed for performing a particular type of investigation, involve also many repetitive tasks that can be organized in general routines to be reused in the future.

To account for this, the suggested workflow for performing analyses in this repository is the following:
1) In `exploratory/`, develop your initial analysis scripts and generate your results without worrying too much about organization. 

2) As the scripts developed in 1. get more mature, transfer them to `analyses/`. Here, the goal is to have well tested and documented analysis pipelines that can be readily understood and employed by other users. For a clean code, try to organize the main analysis script as a wrapper (https://en.wikipedia.org/wiki/Wrapper_function; it could be e.g. `analyses/analysis1/run1.py`) that calls subroutines for each task performed. Subroutines that are specific to that particular analysis can be locally defined under `analyses/` (e.g. `analyses/analysis1/aux1.py`). Subroutines of a more general nature should be defined under `src/monan_analysis` in one of the available modules depending on its purpose (utils, io, plotting, stats, etc.). The goal is to integrate them into our `src/` packages, thereby facilitating future reuse.

In both steps 1) and 2) the user can take advantage of the already defined functions in our packages under `src/`. To call them, one just needs to import the respective package as usually done in python, e.g., to import a plotting function do

```
from monan_analysis.plots import example_function_plots
```

For developing the project please follow the workflow

new branch (name abbreviation/feature, e.g. gtm/repo-organization) --> code modifications -->  open pull request and assign reviewers --> after reviewers' approval, merge into `main` branch.


