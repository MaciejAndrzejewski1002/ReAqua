import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from reaqua.core import synthetic  # noqa: E402

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join("data", "sample")
    for role, path in synthetic.write_scene(target, size=400, seed=7).items():
        print(role, path)
