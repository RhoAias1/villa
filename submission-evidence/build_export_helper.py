"""Compile one verification source against either build's exact native link dependencies."""
from pathlib import Path
import argparse
import shlex
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("build", type=Path)
parser.add_argument("source_tree", type=Path)
args = parser.parse_args()
project = Path(__file__).resolve().parent
build = args.build.resolve()
line = subprocess.check_output(["ninja", "-t", "commands", "vc_object_export"], cwd=build, text=True).splitlines()[-1]
tokens = shlex.split(line)
if tokens[:2] == [":", "&&"]:
    tokens = tokens[2:]
if tokens[-2:] == ["&&", ":"]:
    tokens = tokens[:-2]
obj = next(i for i, token in enumerate(tokens) if token.endswith("vc_object_export.cpp.o"))
tokens[obj] = str(project / "verify_fiber_exports.cpp")
tokens[tokens.index("-o") + 1] = str(build / "verify_fiber_exports")
tokens[1:1] = ["-std=c++20", "-I" + str(args.source_tree.resolve() / "include"), "-I/opt/homebrew/include"]
print(shlex.join(tokens), flush=True)
subprocess.run(tokens, cwd=build, check=True)
