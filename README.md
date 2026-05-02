# Personal Library

A local LLM-maintained wiki for research papers, inspired by Karpathy's "LLM wiki" idea.

## Setup
```
conda env create -f environment.yml
conda activate personal_library
cp .env.example .env  # then edit
```

## Usage (CLI)
```
python cli.py ingest path/to/paper.pdf
python cli.py query "What is the latest on diffusion policies for driving?"
python cli.py rebuild-index
```

See `docs/superpowers/specs/` for design.
