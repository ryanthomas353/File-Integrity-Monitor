"""Create or check a SHA-256 baseline for one file or folder (Python 3.12+)."""
# Standard-library modules for hashing, JSON baseline storage, path handling, and file types.
import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path

# Keep baseline records and the result log beside this script.
PROJECT = Path(__file__).resolve().parent
BASELINES = PROJECT / "file_baselines"
RESULTS = PROJECT / "results.txt"


# Read a file as bytes and calculate its SHA-256 digest.
def file_hash(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


# Propagate directory traversal failures instead of silently skipping files.
def stop_on_error(error):
    raise error  # An unreadable folder must not look empty.


# Capture the current state of either a single regular file or an entire folder.
def snapshot(path, mode):
    # A single-file baseline stores one content hash.
    if stat.S_ISREG(mode):
        return {"sha256": file_hash(path)}
    # Reject special file types, including symbolic links.
    if not stat.S_ISDIR(mode):
        raise ValueError("Choose a regular file or folder.")

    # For folders, map each relative file path to its SHA-256 hash.
    files = {}
    for folder, dirs, names in path.walk(on_error=stop_on_error):
        # Avoid including the application's generated baseline directory.
        dirs[:] = [name for name in dirs if folder / name != BASELINES]
        for name in names:
            item = folder / name
            # Ignore the results log and hash only regular files.
            if item != RESULTS and stat.S_ISREG(item.lstat().st_mode):
                files[item.relative_to(path).as_posix()] = file_hash(item)
    return {"files": files}


# Build a readable summary of a baseline or integrity-check result.
def format_result(status, path, data):
    lines = [f"{status}  {path}"]
    # Missing targets display hashes from the previously saved baseline.
    label = "Saved SHA-256" if status == "MISSING" else "SHA-256"
    if "sha256" in data:
        lines.append(f"{label}: {data['sha256']}")
    else:
        # Sort folder entries to produce stable, predictable output.
        for name, digest in sorted(data["files"].items()):
            lines.append(f"{label}: {digest}  {name}")
    return "\n".join(lines)


# Prompt for an action and target, then create or verify its stored baseline.
def run():
    # Only baseline creation and verification are supported.
    choice = input("1 - Create a baseline\n2 - Check a baseline\nChoose 1 or 2: ").strip()
    if choice not in ("1", "2"):
        raise ValueError("Choose 1 or 2.")
    # Strip whitespace and surrounding double quotes from pasted Windows paths.
    entered = input("Enter a file or folder path: ").strip().strip('"')
    if not entered:
        raise ValueError("Enter a path.")
    # Convert the input to an absolute path and resolve its parent directory.
    path = Path(os.path.abspath(Path(entered).expanduser()))
    path = path.parent.resolve() / path.name
    # Prevent the application from monitoring its own generated output.
    if path == RESULTS or path.is_relative_to(BASELINES):
        raise ValueError("Choose a path outside the monitor's own output files.")

    # Each absolute path gets a separate baseline, including paths with the same name.
    # Use a normalized-path hash to name the corresponding JSON baseline file.
    key = hashlib.sha256(os.path.normcase(str(path)).encode("utf-8")).hexdigest()
    record = BASELINES / (key + ".json")
    # Option 1: take a snapshot and create a new baseline without overwriting one.
    if choice == "1":
        data = snapshot(path, path.lstat().st_mode)
        BASELINES.mkdir(exist_ok=True)
        with record.open("x", encoding="utf-8") as file:
            json.dump({"path": str(path), **data}, file, indent=2)
        return format_result("BASELINE CREATED", path, data)

    # Option 2: load the existing baseline before checking the target.
    try:
        saved = json.loads(record.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError("Create a baseline for this path first.") from None
    # If the original target no longer exists, report its saved state as missing.
    try:
        mode = path.lstat().st_mode
    except (FileNotFoundError, NotADirectoryError):
        return format_result("MISSING", path, saved)
    # Recalculate hashes and compare the complete stored and current values.
    current = snapshot(path, mode)
    # Folder equality compares both relative filenames and their content hashes.
    field = "files" if "files" in current else "sha256"
    unchanged = field in saved and saved[field] == current[field]
    status = "UNCHANGED" if unchanged else "MODIFIED"
    return format_result(status, path, current)


# Run the interactive program only when this file is executed directly.
if __name__ == "__main__":
    # Convert expected input and file-system errors into user-facing messages.
    try:
        result = run()
    except FileExistsError:
        result = "ERROR  A baseline already exists for this path."
    except (ValueError, OSError) as error:
        result = f"ERROR  {error}"
    # Timestamp every result in UTC for consistent audit records.
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = f"{stamp}  {result}"
    print(line)
    # Append results to a persistent text log, reporting write failures.
    try:
        with RESULTS.open("a", encoding="utf-8") as log:
            print(line, file=log)
    except OSError as error:
        raise SystemExit(f"Could not save results.txt: {error}")
