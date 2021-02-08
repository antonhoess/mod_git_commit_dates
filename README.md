# mod_git_commit_dates
This program aims to modify all commit dates of a given local git repository according to a given rule.

## Install
### Create a conda environment
```bash
conda init bash # => Open new terminal
conda create --name mod_git_commit_dates python=3.8
conda install --name mod_git_commit_dates gitpython
```

## Run
### Activate the conda environment and start the program
```bash
cd mod_git_commit_dates/
conda activate mod_git_commit_dates
python mod_git_commit_dates.py --path <GIT-DIR>
```
