# Python 3.11 Setup Instructions

This project requires Python 3.11 or higher. Here's how to set it up:

## Option 1: Using pyenv (Recommended)

```bash
# Install pyenv if you haven't already
brew install pyenv

# Install Python 3.11
pyenv install 3.11.9

# Set Python 3.11 for this project
cd /Users/morford/GitHub/cube-mcp
pyenv local 3.11.9

# Verify Python version
python --version  # Should show Python 3.11.9
```

## Option 2: Using Homebrew directly

```bash
# Install Python 3.11
brew install python@3.11

# Create a virtual environment with Python 3.11
python3.11 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install the project
make install-dev
```

## Option 3: Using conda/miniconda

```bash
# Create a new conda environment with Python 3.11
conda create -n cube-mcp python=3.11

# Activate the environment
conda activate cube-mcp

# Install the project
make install-dev
```

## After Python 3.11 is installed

Once you have Python 3.11 set up, you can install the development dependencies:

```bash
# Make sure you're in the project directory
cd /Users/morford/GitHub/cube-mcp

# Install development dependencies
make install-dev

# Or manually:
pip install -e ".[dev]"
```

## Verify Installation

```bash
# Check Python version
python --version  # Should be 3.11.x

# Run tests
make test

# Run linting
make lint
```