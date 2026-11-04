#!/usr/bin/env python3
"""Build, inspect or export SnowyHome development icon packs; never installs them."""
import argparse
import json
from pathlib import Path
import iconpack


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    build = sub.add_parser('build'); build.add_argument('source', type=Path); build.add_argument('output', type=Path)
    inspect = sub.add_parser('inspect'); inspect.add_argument('package', type=Path)
    export = sub.add_parser('export'); export.add_argument('package', type=Path); export.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.action == 'export': print('Exported (not installed):', iconpack.export(args.package, args.output)); return
    result = iconpack.build(args.source, args.output) if args.action == 'build' else iconpack.inspect(args.package)
    print(json.dumps({**result[0], 'packageSha256': result[3]}, indent=2))


if __name__ == '__main__': main()
