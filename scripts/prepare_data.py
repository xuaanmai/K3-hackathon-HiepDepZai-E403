from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.data_loader import prepare_data


def main() -> None:
    chunks, issues, output_path = prepare_data()
    print(f"Prepared {len(chunks)} chunks")
    print(f"Saved to {output_path}")
    if issues["empty"]:
        print(f"Skipped {len(issues['empty'])} empty chunks")
    if issues["duplicate"]:
        print(f"Skipped {len(issues['duplicate'])} duplicate chunks")
    if issues["long"]:
        print(f"Found {len(issues['long'])} chunks longer than the safety threshold")


if __name__ == "__main__":
    main()
