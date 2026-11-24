#!/usr/bin/env python3
"""Inventory reviewed package bytes; --write is explicit and never approves behavior."""
import argparse
import hashlib
import json
from pathlib import Path

EXCLUDED = {'asset-manifest.json', 'verification-summary.json'}

def inventory(root):
    entries = []
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root).as_posix()
        if not path.is_file() or rel in EXCLUDED or path.name == '.DS_Store' or '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        if path.is_symlink():
            raise ValueError(f'Symlink not allowed: {rel}')
        data = path.read_bytes()
        entries.append({'path': rel, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    return {'schemaVersion': '1.0.0', 'domain': 'energyInfrastructure',
            'purpose': 'Reviewed offline asset-integrity inventory, not domain admission evidence',
            'excludedOutputs': sorted(EXCLUDED),
            'excludedFilePatterns': ['.DS_Store', '__pycache__', '*.pyc'], 'files': entries}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    value = inventory(root)
    target = root / 'asset-manifest.json'
    if args.write:
        target.write_text(json.dumps(value, indent=2) + '\n')
    elif json.loads(target.read_text()) != value:
        raise SystemExit('Asset manifest differs; review changes before explicit --write')
    print(json.dumps({'result': 'PASS', 'hashedAssets': len(value['files']), 'manifestWritten': args.write}))

if __name__ == '__main__':
    main()
