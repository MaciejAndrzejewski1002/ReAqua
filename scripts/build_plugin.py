import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "src", "reaqua")
TARGET = os.path.join(ROOT, "dist", "reaqua.zip")
SKIP_DIRS = {"__pycache__"}
SKIP_EXT = (".pyc", ".pyo")


def build() -> str:
    os.makedirs(os.path.dirname(TARGET), exist_ok=True)
    with zipfile.ZipFile(TARGET, "w", zipfile.ZIP_DEFLATED) as archive:
        for folder, dirs, files in os.walk(SOURCE):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in sorted(files):
                if name.endswith(SKIP_EXT):
                    continue
                path = os.path.join(folder, name)
                archive.write(path, os.path.join("reaqua", os.path.relpath(path, SOURCE)))
        license_path = os.path.join(ROOT, "LICENSE")
        if os.path.exists(license_path):
            archive.write(license_path, os.path.join("reaqua", "LICENSE"))
    return TARGET


if __name__ == "__main__":
    print(build())
    sys.exit(0)
