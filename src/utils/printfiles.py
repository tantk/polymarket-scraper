from pathlib import Path

root_dir = Path(".")

# Filter out any path that has 'venv' in its directory parts
for path in root_dir.rglob("*"):
    if path.is_file() and "venv" not in path.parts:
        print(path)