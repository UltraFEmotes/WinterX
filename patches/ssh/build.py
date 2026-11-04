#!/usr/bin/env python3
"""Build the optional SSH library JAR; never install, generate user keys or start a server."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import subprocess
import tempfile
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
DEPS = (
    ('org.apache.sshd', 'sshd-core', '2.20.1', '267525ebf83dbb5a9c72f372c8ba03a1512b1d27129b0271c56f68c73814534f'),
    ('org.apache.sshd', 'sshd-common', '2.20.1', '19212364751ca6b0227298fa72da06338eba1cc8d7c8e11b35115f7590dd2b59'),
    ('org.apache.sshd', 'sshd-sftp', '2.20.1', '79912130d3903adc0f35690d2654f138cd82b5242ae06b36417c4b9b383577f0'),
    ('org.slf4j', 'slf4j-api', '2.0.17', '7b751d952061954d5abfed7181c1f645d336091b679891591d63329c622eb832'),
)


def dependencies(directory):
    directory.mkdir(parents=True, exist_ok=True)
    def download(dep):
        group, artifact, version, expected = dep
        path = directory / (artifact + '.jar')
        if path.exists():
            raw = path.read_bytes()
        else:
            url = 'https://repo.maven.apache.org/maven2/' + group.replace('.', '/') + '/' + artifact + '/' + version + '/' + artifact + '-' + version + '.jar'
            with urllib.request.urlopen(url, timeout=30) as response: raw = response.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('SSH dependency checksum mismatch: ' + artifact)
        if not path.exists():
            with path.open('xb') as out: out.write(raw)
        return path
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(download, DEPS))


def build(output, deps, javac='javac'):
    if output.exists(): raise ValueError('Output must be a new JAR')
    jars = dependencies(deps)
    with tempfile.TemporaryDirectory(prefix='winterx-ssh-build-') as tmp:
        classes = Path(tmp) / 'classes'; classes.mkdir()
        subprocess.run([javac, '--release', '8', '-cp', ':'.join(map(str, jars)), '-d', str(classes),
                        *map(str, sorted((HERE / 'src').rglob('*.java')))], check=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as out:
            for path in sorted(classes.rglob('*.class')): out.write(path, path.relative_to(classes).as_posix())
            for dep, path in zip(DEPS, jars):
                with zipfile.ZipFile(path) as jar:
                    for name in jar.namelist():
                        if name.endswith('/') or name.startswith('META-INF/versions/') or name.endswith('module-info.class'): continue
                        if name.startswith('META-INF/'):
                            if name.endswith(('LICENSE', 'NOTICE', 'LICENSE.txt', 'NOTICE.txt')):
                                out.writestr('licenses/' + dep[1] + '/' + name.split('/')[-1], jar.read(name))
                            continue
                        out.writestr(name, jar.read(name))
    print('Built optional SSH library (not installed or listening):', output)
    print('SHA-256:', hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path); parser.add_argument('--deps', type=Path, required=True)
    parser.add_argument('--javac', default='javac'); args = parser.parse_args()
    build(args.output, args.deps, args.javac)
