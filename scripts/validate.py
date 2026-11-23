#!/usr/bin/env python3
"""Validate public source and optionally prepared inputs without building an ISO."""
from pathlib import Path
import argparse,json,subprocess,sys
from prepare import ROOT,LOCAL,source_digest

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared',action='store_true')
    args=parser.parse_args()
    checked=0
    for path in (ROOT/'config').rglob('*'):
        if not path.is_file():continue
        raw=path.read_bytes()
        if path.suffix=='.json':json.loads(raw)
        if raw.startswith(b'#!/usr/bin/python3') or path.suffix=='.py':compile(raw,str(path),'exec')
        if raw.startswith((b'#!/bin/sh',b'#!/usr/bin/env bash',b'#!/bin/bash')):
            subprocess.run(['bash','-n',str(path)],check=True)
        checked+=1
    for path in (ROOT/'scripts').glob('*.py'):compile(path.read_bytes(),str(path),'exec')
    subprocess.run(['bash','-n',str(ROOT/'scripts/build.sh')],check=True)
    for name,target in json.loads((ROOT/'config/symlinks.json').read_text()).items():
        rel=Path(name)
        assert not rel.is_absolute() and '..' not in rel.parts
        if target.startswith('/'):
            assert target=='/dev/null' or target.startswith('/usr/share/live/build/hooks/')
    if args.prepared:
        stage=LOCAL/'prepared'
        metadata=json.loads((stage/'preparation.json').read_text())
        assert metadata['source_sha256']==source_digest(),'Source changed; prepare a new tree'
        overlay=stage/'config/includes.chroot'
        runtime=json.loads((overlay/'usr/local/share/live-apps/codex-runtime.json').read_text())
        for name in ('node','cli'):assert (overlay/runtime[name].lstrip('/')).is_file(),runtime[name]
        subprocess.run([str(overlay/runtime['node'].lstrip('/')),'--version'],check=True)
        for name in ('code','veracrypt'):
            assert list((stage/'config/packages.chroot').glob(name+'_*.deb'))
        policy=json.loads((overlay/'etc/live-profile/store.json').read_text())
        assert policy['id']==(LOCAL/'profile-id').read_text().strip()
        assert (overlay/'etc/systemd/system/swap.target').is_symlink()
        assert (overlay/'usr/local/bin/poweroff').readlink()==Path('live-power')
        assert not list(overlay.rglob('auth.json'))
        for path in (stage/'config/hooks').rglob('*.chroot'):assert path.exists(),path
        js=overlay/'usr/share/gnome-shell/extensions/live-safe-power@debian-live/extension.js'
        subprocess.run([str(overlay/runtime['node'].lstrip('/')),'--input-type=module','--check'],input=js.read_bytes(),check=True)
    print(f'Validated {checked} config files'+(' and prepared inputs' if args.prepared else '')+'. No ISO built.')

if __name__=='__main__':main()
