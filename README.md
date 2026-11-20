# File Integrity Monitor

Use Python 3.12 or later. From the project folder, run `py fim.py` on Windows or `python3 fim.py` on Linux or macOS.

1. Choose **1** and enter a file or folder path to save its baseline.
2. Later, run the script again, choose **2**, and enter the same path.

Each run checks one selected path. A file check compares its SHA-256 hash. A folder check compares the relative paths and SHA-256 hashes of all regular files in the folder and its subfolders. It reports one result for the selected path.

| Result | Meaning |
| --- | --- |
| UNCHANGED | The current file contents or folder file list and hashes match the baseline. |
| MODIFIED | The selected file changed, or a file inside the folder was added, removed, renamed or edited. Replacing a file with a folder, or the reverse, also counts as a modification. |
| MISSING | The selected path had a baseline and has since disappeared. |

Results are printed and appended with a UTC timestamp to `results.txt` beside the script. Baselines are stored in `file_baselines/`. Creating a second baseline for the same path is refused. Keep the initial files and their baselines trustworthy.

Folder comparisons skip symbolic links and the monitor’s own results and baseline records. Empty subfolders and file attributes such as permissions are outside the comparison. A read failure is reported as an error.
