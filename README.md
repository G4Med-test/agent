# G4Med Agent

This agent periodically polls the dispatcher repository for pending jobs, executes them in an isolated Apptainer container, and publishes results.

## Features
- GitHub Issue-based job claiming.
- Automatic load balancing (preferred repos + priority-based picking).
- Runs all macro files found in the specified input folder.
- Stores results in an output folder and attaches to a new release.
- Closes the issue with result links.

## Configuration
Edit `config.json` to define:
- Dispatcher repo.
- Agent server name.
- Polling interval.
- Maximum concurrent jobs.
- Preferred repositories.

## Usage
Build the container:
```bash
sudo apptainer build agent.sif apptainer_agent.def

This repository provides all you need to build an Apptainer (Singularity) container with the `gh` CLI and an automatic polling script to monitor GitHub workflow runs and submit an LSF job when a successful run is detected.

## Contents
- **Apptainer.def** — Container definition with `GH_TOKEN` support for private repositories or workflow triggering
- **check_and_wait.sh** — Script to poll GitHub workflow status and submit LSF jobs
- **crontab_example.txt** — Example crontab configurations

## Build the container

```bash
apptainer build gh.sif Apptainer.def
```

## Example crontab usage

```bash
0 8 * * * GH_TOKEN=your_token_here apptainer run --bind /path/to/state_folder:/state /path/to/gh.sif >> /path/to/logfile.log 2>&1
```