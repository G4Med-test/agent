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
