"""Resolve canonical domain slugs to explicit factory directories, never runtime aliases."""
import json
from pathlib import Path
import re

SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
COMPONENT = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')
CONFIG = Path('domains/factory-domain-paths.json')

def require(ok, message):
    if not ok:
        raise ValueError(message)

def inside(repo, path):
    require(path.resolve().is_relative_to(repo.resolve()), 'Factory path escapes repository')
    current = path
    while current != repo:
        require(not current.is_symlink(), 'Symlink factory paths are forbidden')
        current = current.parent

def aliases(repo):
    repo = Path(repo)
    config = repo / CONFIG
    inside(repo, config)
    if not config.exists():
        return {}
    value = json.loads(config.read_text())
    require(isinstance(value, dict) and set(value) == {'schemaVersion', 'purpose', 'aliases'}, 'Invalid factory path configuration')
    require(value['schemaVersion'] == '1.0.0' and isinstance(value['purpose'], str) and value['purpose'].strip(), 'Invalid factory path version/purpose')
    result = value['aliases']
    require(isinstance(result, dict), 'Factory aliases must be an object')
    for domain, folder in result.items():
        require(bool(SLUG.fullmatch(domain)), 'Invalid canonical factory domain slug')
        require(isinstance(folder, str) and len(folder) <= 128 and bool(COMPONENT.fullmatch(folder)), 'Invalid factory directory component')
    require(len({f.casefold() for f in result.values()}) == len(result), 'Duplicate factory directory aliases')
    manifest = repo / 'domains/domain-manifest.json'
    inside(repo, manifest)
    owners = set(result)
    if manifest.exists():
        owners.update(json.loads(manifest.read_text())['domains'])
    factory = repo / 'machine_factory/domains'
    inside(repo, factory)
    if factory.exists():
        owners.update(p.name for p in factory.iterdir() if p.is_dir() and SLUG.fullmatch(p.name))
    for domain, folder in result.items():
        require(not any(other != domain and folder.casefold() == other.casefold() for other in owners), 'Factory alias shadows another canonical domain')
        target = factory / folder
        inside(repo, target)
        old = factory / domain
        inside(repo, old)
        require(folder == domain or not (old / 'deployments').exists(), 'Existing deployment history cannot be redirected by a factory alias')
    return result

def factory_directory(repo, domain):
    repo = Path(repo)
    require(isinstance(domain, str) and bool(SLUG.fullmatch(domain)), 'Invalid canonical factory domain slug')
    directory = repo / 'machine_factory/domains' / aliases(repo).get(domain, domain)
    inside(repo, directory)
    return directory
