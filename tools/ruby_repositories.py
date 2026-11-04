"""HTTPS repository support for Ruby's declarative .springys packages."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

import ruby_packages
import springys

INDEX_LIMIT = 512 * 1024
PACKAGE_LIMIT = springys.MAX_ZIP
MAX_PACKAGES = 100
SHA = re.compile(r'^[0-9a-f]{64}$')


def https_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError('Invalid HTTPS URL')
    parts = urlsplit(value)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.fragment:
        raise ValueError('Repository URLs must be HTTPS without credentials or fragments')
    return value


def download(url, limit):
    url = https_url(url)
    req = Request(url, headers={'User-Agent': 'Ruby-Spring/1.0', 'Accept': '*/*'})
    with urlopen(req, timeout=15) as response:
        https_url(response.geturl())
        length = response.headers.get('Content-Length')
        if length and int(length) > limit:
            raise ValueError('Download exceeds size limit')
        payload = response.read(limit + 1)
        if len(payload) > limit:
            raise ValueError('Download exceeds size limit')
        return payload


def atomic_json(path, value):
    ruby_packages._atomic(path, json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8'))


class Repositories:
    def __init__(self, app_files, packages, fetch=download, builtin_root=None):
        self.files = Path(app_files)
        self.packages = packages
        self.fetch = fetch
        self.builtin_root = Path(builtin_root).resolve(strict=True) if builtin_root else None
        self.sources = self.files / 'sources.json'
        self.catalogue = self.files / 'repository-catalogue.json'

    def read_sources(self):
        if not self.sources.exists():
            return []
        data = json.loads(self.sources.read_text(encoding='utf-8'))
        if not isinstance(data, list) or len(data) > 50:
            raise ValueError('Invalid source list')
        return [https_url(u) for u in data]

    def add(self, url):
        url = https_url(url.strip())
        sources = self.read_sources()
        if url not in sources:
            if len(sources) >= 50:
                raise ValueError('Too many repositories')
            sources.append(url)
            atomic_json(self.sources, sources)
        return self.refresh()

    def remove(self, url):
        sources = self.read_sources()
        if url not in sources:
            raise ValueError('Repository not found')
        sources.remove(url)
        atomic_json(self.sources, sources)
        return self.refresh()

    def refresh(self):
        sources, items = [], []
        installed = self.packages.registry.list()
        self.packages.imports.mkdir(parents=True, exist_ok=True)
        urls = (['winterx:built-in'] if self.builtin_root else []) + self.read_sources()
        for url in urls:
            local = url == 'winterx:built-in'
            source = {'url': url, 'name': url, 'error': None, 'builtIn': local}
            try:
                raw_index = (self.builtin_root / 'index.json').read_bytes() if local else self.fetch(url, INDEX_LIMIT)
                if len(raw_index) > INDEX_LIMIT: raise ValueError('Index exceeds size limit')
                index = json.loads(raw_index.decode('utf-8'))
                if not isinstance(index, dict) or index.get('format') != 'winterx.repository/1':
                    raise ValueError('Unsupported repository format')
                if not isinstance(index.get('name'), str) or not 1 <= len(index['name']) <= 80:
                    raise ValueError('Invalid repository name')
                entries = index.get('packages')
                if not isinstance(entries, list) or len(entries) > MAX_PACKAGES:
                    raise ValueError('Invalid repository package list')
                source['name'] = index['name']
                for entry in entries:
                    try:
                        if not isinstance(entry, dict) or not SHA.fullmatch(entry.get('sha256', '')):
                            raise ValueError('Invalid package hash')
                        if local:
                            relative = Path(entry['url'])
                            if relative.is_absolute() or '..' in relative.parts:
                                raise ValueError('Invalid built-in package path')
                            package_path = (self.builtin_root / relative).resolve(strict=True)
                            if not package_path.is_relative_to(self.builtin_root) or not package_path.is_file():
                                raise ValueError('Invalid built-in package path')
                            if package_path.stat().st_size > PACKAGE_LIMIT:
                                raise ValueError('Package exceeds size limit')
                            raw = package_path.read_bytes()
                        else:
                            package_url = https_url(urljoin(url, entry['url']))
                            raw = self.fetch(package_url, PACKAGE_LIMIT)
                        if hashlib.sha256(raw).hexdigest() != entry['sha256']:
                            raise ValueError('Package checksum mismatch')
                        filename = 'repo-' + entry['sha256'] + '.springys'
                        path = self.packages.imports / filename
                        ruby_packages._atomic(path, raw)
                        metadata, images = springys.inspect(path, entry['sha256'])
                        art = {}
                        for name, payload in images.items():
                            target = 'package-art/' + hashlib.sha256(payload).hexdigest() + Path(name).suffix.lower()
                            ruby_packages._atomic(self.files / target, payload)
                            art[name] = target
                        metadata.update(filename=filename, source=url, sourceName=source['name'],
                                        installedVersion=installed.get(metadata['id'], {}).get('version'),
                                        installedSha256=installed.get(metadata['id'], {}).get('sha256'))
                        icon = metadata['icon']
                        metadata['icon'] = ruby_packages.icon_thumbnail(self.files, images[icon]) if icon else None
                        metadata['previews'] = [art[name] for name in metadata['previews']]
                        items.append(metadata)
                    except (KeyError, TypeError, ValueError, OSError) as exc:
                        source['error'] = 'Some packages could not be loaded: ' + str(exc)[:180]
            except (ValueError, OSError, UnicodeError) as exc:
                source['error'] = str(exc)[:200]
            sources.append(source)
        result = {'sources': sources, 'packages': items}
        atomic_json(self.catalogue, result)
        return result
