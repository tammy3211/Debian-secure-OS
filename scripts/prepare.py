#!/usr/bin/env python3
"""Prepare a disposable Debian live-build tree; this script never builds an ISO."""
from pathlib import Path
import argparse,base64,hashlib,json,os,shutil,subprocess,sys,tarfile,tempfile,urllib.request,uuid

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'.local'

def digest(path,algorithm='sha256'):
    result=hashlib.new(algorithm)
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024),b''):result.update(chunk)
    return result.digest()

def source_digest():
    result=hashlib.sha256()
    for path in sorted((ROOT/'config').rglob('*')):
        if path.is_file():
            result.update(path.relative_to(ROOT).as_posix().encode()+b'\0'+path.read_bytes())
    return result.hexdigest()

def fetch(cache,name,url,checksum,algorithm,offline):
    target=cache/name
    if not target.is_file():
        if offline or not url:
            raise RuntimeError(f'Missing dependency: {target.name}. See docs/BUILD.md.')
        print('Downloading '+name,flush=True)
        partial=target.with_suffix(target.suffix+'.part')
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'Portable-Live-OS-build-preparation'})
            with urllib.request.urlopen(request,timeout=120) as source,partial.open('wb') as dest:
                shutil.copyfileobj(source,dest)
            if digest(partial,algorithm)!=checksum:raise RuntimeError('Checksum mismatch: '+name)
            partial.replace(target)
        finally:partial.unlink(missing_ok=True)
    if digest(target,algorithm)!=checksum:raise RuntimeError('Checksum mismatch: '+name)
    return target

def unpack(archive,dest):
    with tarfile.open(archive) as stream:stream.extractall(dest,filter='data')
    children=list(dest.iterdir())
    if len(children)!=1 or not children[0].is_dir():raise RuntimeError('Unexpected archive layout: '+archive.name)
    return children[0]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline',action='store_true',help='Use verified local downloads only')
    args=parser.parse_args()
    if sys.platform!='linux' or sys.version_info<(3,12):raise SystemExit('Run on Debian 13 with Python 3.12 or later.')
    if not shutil.which('lb'):raise SystemExit('Install live-build first; see docs/BUILD.md.')
    LOCAL.mkdir(exist_ok=True)
    if LOCAL.is_symlink():raise SystemExit('Refusing linked local directory')
    prepared=LOCAL/'prepared'
    if prepared.exists():raise SystemExit('Prepared tree already exists; move it aside before preparing again.')
    cache=LOCAL/'downloads';cache.mkdir(exist_ok=True)
    if cache.is_symlink():raise SystemExit('Refusing linked download directory')
    assets=json.loads((ROOT/'config/assets.json').read_text())
    files={entry['kind']:fetch(cache,entry['file'],entry['url'],bytes.fromhex(entry['sha256']),'sha256',args.offline)
           for entry in assets['assets']}
    codex=json.loads((ROOT/'config/codex/package-lock.json').read_text())
    codex_files={}
    for package in ('@openai/codex','@openai/codex-linux-x64'):
        entry=codex['packages']['node_modules/'+package]
        algorithm,checksum=entry['integrity'].split('-',1)
        name=package.split('/')[-1]+'-'+entry['version']+'.tgz'
        codex_files[package]=fetch(cache,name,entry['resolved'],base64.b64decode(checksum),algorithm,args.offline)
    with tempfile.TemporaryDirectory(prefix='prepare-',dir=LOCAL) as temp:
        stage=Path(temp)/'tree';stage.mkdir()
        options=json.loads((ROOT/'config/build.json').read_text())
        subprocess.run(['lb','config','--distribution',options['distribution'],'--architectures',options['architecture'],
          '--archive-areas',options['archive_areas'],'--binary-images',options['image_type'],
          '--bootloaders',options['bootloaders'],'--bootappend-live',options['bootappend_live'],
          '--debian-installer','none','--checksums','sha256','--memtest','none',
          '--apt-recommends','true','--security','true','--updates','true'],cwd=stage,check=True)
        for folder in ('package-lists','preseed','hooks','includes.chroot'):
            shutil.copytree(ROOT/'config'/folder,stage/'config'/folder,dirs_exist_ok=True)
        for name,target in json.loads((ROOT/'config/symlinks.json').read_text()).items():
            path=stage/'config'/name
            if not path.parent.resolve().is_relative_to((stage/'config').resolve()):raise RuntimeError('Unsafe link path')
            path.parent.mkdir(parents=True,exist_ok=True)
            path.unlink(missing_ok=True);path.symlink_to(target)
        overlay=stage/'config/includes.chroot'
        for path in overlay.rglob('*'):
            if path.is_file() and not path.is_symlink():
                raw=path.read_bytes().replace(b'\r\n',b'\n');path.write_bytes(raw)
                path.chmod(0o755 if raw.startswith(b'#!') else 0o644)
        for path in (stage/'config/hooks').rglob('*.chroot'):
            if not path.is_symlink():path.chmod(0o755)
        debs=stage/'config/packages.chroot';debs.mkdir(exist_ok=True)
        for entry in assets['assets']:
            if entry['kind']=='deb':shutil.copy2(cache/entry['file'],debs/entry['file'])
        node=unpack(files['node'],Path(temp)/'node')
        nvm=unpack(files['nvm'],Path(temp)/'nvm')
        target=overlay/'etc/skel/.nvm';target.mkdir(parents=True)
        for name in ('nvm.sh','nvm-exec','bash_completion','LICENSE.md','README.md'):shutil.copy2(nvm/name,target/name)
        version=assets['node_version'];node_dest=target/'versions/node'/version
        shutil.copytree(node,node_dest,symlinks=True)
        (target/'alias').mkdir();(target/'alias/default').write_text(version+'\n')
        live_codex=overlay/'opt/live-codex';live_codex.mkdir(parents=True)
        for name in ('package.json','package-lock.json'):shutil.copy2(ROOT/'config/codex'/name,live_codex/name)
        for package,archive in codex_files.items():
            extracted=unpack(archive,Path(temp)/package.split('/')[-1])
            shutil.copytree(extracted,live_codex/'node_modules'/package,symlinks=True)
        profile_id=LOCAL/'profile-id'
        if not profile_id.exists():profile_id.write_text(str(uuid.uuid4())+'\n')
        policy=overlay/'etc/live-profile/store.json';policy.parent.mkdir(parents=True,exist_ok=True)
        policy.write_text(json.dumps({'version':1,'id':str(uuid.UUID(profile_id.read_text().strip()))},indent=2)+'\n')
        (stage/'preparation.json').write_text(json.dumps({'source_sha256':source_digest(),'iso_built':False},indent=2)+'\n')
        stage.rename(prepared)
    print('Prepared: '+str(prepared)+' (no ISO build performed)',flush=True)

if __name__=='__main__':
    try:main()
    except (RuntimeError,OSError,subprocess.CalledProcessError) as error:raise SystemExit(str(error))
