"""Allowlisted desktop preferences only. USB data is never evaluated as code."""
from pathlib import Path
import configparser
import contextlib
import fcntl
import datetime
import hashlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import uuid
import xml.etree.ElementTree as ET

import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

SCHEMAS = {
 'org.gnome.desktop.interface': 'gtk-theme icon-theme cursor-theme cursor-size font-name document-font-name monospace-font-name text-scaling-factor color-scheme clock-format clock-show-date clock-show-seconds show-battery-percentage enable-animations',
 'org.gnome.desktop.peripherals.mouse': 'speed accel-profile natural-scroll left-handed double-click drag-threshold middle-click-emulation',
 'org.gnome.desktop.peripherals.touchpad': 'speed natural-scroll tap-to-click two-finger-scrolling-enabled edge-scrolling-enabled left-handed disable-while-typing click-method send-events',
 'org.gnome.desktop.input-sources': 'sources xkb-options per-window show-all-sources',
 'org.gnome.desktop.wm.preferences': 'button-layout action-double-click-titlebar action-middle-click-titlebar action-right-click-titlebar focus-mode resize-with-right-button num-workspaces titlebar-font',
 'org.gnome.settings-daemon.plugins.power': 'sleep-inactive-ac-type sleep-inactive-ac-timeout sleep-inactive-battery-type sleep-inactive-battery-timeout idle-dim ambient-enabled power-button-action',
 'org.gnome.desktop.session': 'idle-delay',
 'org.gnome.desktop.screensaver': 'lock-enabled lock-delay',
 'org.gnome.desktop.background': 'picture-uri picture-uri-dark picture-options primary-color secondary-color color-shading-type',
 'org.gnome.desktop.sound': 'event-sounds input-feedback-sounds theme-name',
 'org.gnome.nautilus.preferences': 'default-folder-viewer show-image-thumbnails thumbnail-limit',
 'org.gtk.Settings.FileChooser': 'show-hidden sort-directories-first',
 'org.gnome.Evince.Default': 'continuous dual-page dual-page-odd-left show-sidebar sizing-mode zoom',
 'org.gnome.settings-daemon.plugins.media-keys': 'volume-up volume-down volume-mute play pause stop next previous',
}
CODE_KEYS = set('editor.fontFamily editor.fontSize editor.fontLigatures editor.tabSize editor.insertSpaces editor.detectIndentation editor.renderWhitespace editor.wordWrap editor.formatOnSave editor.minimap.enabled editor.rulers editor.lineNumbers editor.cursorStyle workbench.colorTheme workbench.iconTheme workbench.sideBar.location workbench.statusBar.visible files.eol files.trimTrailingWhitespace files.insertFinalNewline files.autoSave files.autoSaveDelay terminal.integrated.fontFamily terminal.integrated.fontSize terminal.integrated.cursorStyle terminal.integrated.defaultProfile.linux window.zoomLevel'.split())
FILES = ('monitors.xml', '.config/Code/User/settings.json', '.config/mimeapps.list',
         '.config/fcitx5/config', '.config/fcitx5/profile', '.config/fcitx5/conf/hangul.conf', '.config/vlc/vlcrc')
HOME = Path.home()
STATUS = Path('/run/live-profile-status.json')
POLICY = Path('/etc/live-profile/store.json')
DEFAULTS = Path('/usr/local/share/live-profile/defaults')
LOCK_DEPTH = 0

def read_json(path, limit=2 * 1024 * 1024):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError('Missing, oversized or linked profile file')
    def invalid(value): raise ValueError('Non-finite JSON number')
    return json.loads(path.read_text(encoding='utf-8-sig'),parse_constant=invalid)

@contextlib.contextmanager
def locked():
    global LOCK_DEPTH
    if LOCK_DEPTH:
        yield
        return
    _,store=state()
    path=store/'.profile.lock'
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX)
        LOCK_DEPTH+=1
        try: yield
        finally: LOCK_DEPTH-=1
    finally: os.close(fd)

def synchronized(function):
    def wrapped(*args,**kwargs):
        with locked(): return function(*args,**kwargs)
    return wrapped

def atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError('Refusing symlink destination')
    temp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('x', encoding='utf-8') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)

def state():
    status = read_json(STATUS, 16384)
    if not status.get('enabled'):
        raise RuntimeError(status.get('message', 'USB profile unavailable'))
    store = Path(status['store'])
    # Only the root-created boot status chooses a location, never the USB JSON.
    if store != Path('/run/live-profile/LiveProfile'):
        raise ValueError('Unexpected profile store')
    policy = read_json(POLICY, 16384)
    marker = read_json(store / 'store.json', 16384)
    if marker.get('id') != policy['id']:
        raise ValueError('USB profile ID mismatch')
    return status, store

def schemas():
    source = Gio.SettingsSchemaSource.get_default()
    for name, keynames in SCHEMAS.items():
        schema = source.lookup(name, True)
        if schema is None or schema.get_path() is None:
            continue
        settings = Gio.Settings.new_full(schema, None, None)
        yield name, settings, [key for key in keynames.split() if schema.has_key(key)]

def settings_export():
    return {name: {key: settings.get_value(key).print_(True) for key in keys}
            for name, settings, keys in schemas()}

def settings_apply(data, reset=False):
    if not isinstance(data, dict): raise ValueError('Invalid desktop settings')
    for name, settings, keys in schemas():
        values = data.get(name, {})
        if not isinstance(values, dict): continue
        for key in keys:
            if reset:
                settings.reset(key)
                continue
            text = values.get(key)
            if not isinstance(text, str) or len(text) > 8192: continue
            try:
                expected = settings.get_default_value(key).get_type()
                variant = GLib.Variant.parse(expected, text, None, None)
                if settings.range_check(key, variant): settings.set_value(key, variant)
            except (GLib.Error, ValueError, TypeError):
                continue
    Gio.Settings.sync()

def parse_ini(text):
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    first=next((line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith(('#',';'))),'')
    parser.read_string(('[General]\n' if first and not first.startswith('[') else '')+text)
    return parser

def format_ini(data):
    return ''.join('[' + section + ']\n' + ''.join(k + '=' + str(v) + '\n' for k,v in values.items()) + '\n'
                   for section, values in data.items())

def jsonc(text):
    result=[];i=0;quoted=False;escaped=False
    while i<len(text):
        char=text[i]
        if quoted:
            result.append(char)
            if escaped: escaped=False
            elif char=='\\': escaped=True
            elif char=='"': quoted=False
            i+=1;continue
        if char=='"': quoted=True;result.append(char);i+=1;continue
        if text[i:i+2]=='//':
            i=text.find('\n',i)
            if i<0: break
            continue
        if text[i:i+2]=='/*':
            end=text.find('*/',i+2)
            if end<0: raise ValueError('Unclosed JSON comment')
            result.append(' ');i=end+2;continue
        if char==',':
            j=i+1
            while j<len(text) and text[j].isspace(): j+=1
            if j<len(text) and text[j] in '}]': i+=1;continue
        result.append(char);i+=1
    clean=''.join(result)
    # Strip trailing commas after removing comments, without touching strings.
    return re.sub(r'("(?:\\.|[^"\\])*"|,\s*(?=[}\]]))',
                  lambda match: match.group(0) if match.group(0).startswith('"') else '',clean)

def filtered_file(relative, text):
    if not isinstance(text, str) or len(text.encode()) > 256 * 1024: raise ValueError('Invalid preference file')
    if relative == '.config/Code/User/settings.json':
        # VS Code accepts JSONC; comments/trailing commas from normal edits are handled.
        source = json.loads(jsonc(text))
        if not isinstance(source, dict): raise ValueError('Invalid Code settings')
        result = {k:v for k,v in source.items() if k in CODE_KEYS and
                  ((isinstance(v,(str,int,float,bool)) and not (isinstance(v,float) and not math.isfinite(v))) or (k=='editor.rulers' and isinstance(v,list) and len(v)<32 and all(type(n)==int and 0<=n<=500 for n in v)))}
        if result.get('terminal.integrated.defaultProfile.linux') not in (None,'bash','zsh','fish'):
            result.pop('terminal.integrated.defaultProfile.linux',None)
        return json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    parser = parse_ini(text)
    output = {}
    for section in parser.sections():
        selected = {}
        for key,value in parser.items(section):
            if len(value)>4096 or '\n' in value or '\r' in value: continue
            accepted = False
            if relative == '.config/mimeapps.list' and section=='Default Applications':
                ids = value.rstrip(';').split(';')
                accepted = bool(re.fullmatch(r'[\w.+-]+/[\w.+-]+',key)) and 0<len(ids)<=10 and all(
                  re.fullmatch(r'[\w.+-]+\.desktop',item) and (Path('/usr/share/applications')/item).is_file() for item in ids)
            elif relative == '.config/fcitx5/config':
                accepted = ((section=='Hotkey' and key in ('EnumerateWithTriggerKeys','ModifierOnlyKeyTimeout')) or
                  (re.fullmatch(r'Hotkey/[A-Za-z]+Keys',section) and key.isdigit()) or
                  (section=='Behavior' and key in ('ActiveByDefault','ShareInputState','resetStateWhenFocusIn','PreeditEnabledByDefault','ShowInputMethodInformation','ShowInputMethodInformationWhenFocusIn')))
            elif relative == '.config/fcitx5/profile':
                accepted = ((re.fullmatch(r'Groups/\d+',section) and key in ('Name','Default Layout','DefaultIM')) or
                  (re.fullmatch(r'Groups/\d+/Items/\d+',section) and key in ('Name','Layout')) or (section=='GroupOrder' and key.isdigit()))
            elif relative == '.config/fcitx5/conf/hangul.conf':
                accepted = ((section=='General' and key in ('Keyboard','AutoReorder','WordCommit','HanjaMode')) or
                  (section in ('HanjaModeToggleKey','PrevPage','NextPage','PrevCandidate','NextCandidate') and key.isdigit()))
            elif relative == '.config/vlc/vlcrc':
                accepted = ((section=='qt' and key in ('qt-minimal-view','qt-maximized','qt-fs-controller','qt-volume-complete')) or
                  (section=='core' and key in ('fullscreen','video-on-top','rate','audio-language','sub-language','sub-margin','sub-text-scale','volume-save')))
            if accepted: selected[key]=value
        if selected or (relative=='.config/fcitx5/config' and re.fullmatch(r'Hotkey/[A-Za-z]+Keys',section)): output[section]=selected
    result=format_ini(output)
    if relative=='.config/fcitx5/conf/hangul.conf': result=result.replace('[General]\n','',1)
    return result

def monitor_xml(text):
    if len(text.encode())>256*1024 or '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('Unsafe monitor XML')
    root=ET.fromstring(text)
    if root.tag!='monitors' or root.attrib.get('version')!='2' or root.find('policy') is not None:
        raise ValueError('Unsupported monitor XML')
    for element in root.iter():
        if element.tag in ('include','xi:include') or len(element.attrib)>8:
            raise ValueError('Unsupported monitor XML content')
    return text

def home_path(relative):
    path = HOME / relative
    if not path.resolve().is_relative_to(HOME.resolve()): raise ValueError('Preference path escaped home')
    for parent in (path,*path.parents):
        if parent==HOME: break
        if parent.is_symlink(): raise ValueError('Linked preference path')
    return path

def audio_export():
    try:
        result=subprocess.check_output(['wpctl','get-volume','@DEFAULT_AUDIO_SINK@'],text=True,stderr=subprocess.DEVNULL,timeout=3)
        value=float(result.split()[1])
        if math.isfinite(value): return {'volume':max(0,min(1,value)), 'muted':'[MUTED]' in result}
    except (OSError,ValueError,subprocess.SubprocessError): pass
    return None

def audio_apply(data):
    volume=data.get('volume',0) if isinstance(data,dict) else 0
    if type(volume) not in (int,float) or not math.isfinite(volume) or not 0<=volume<=1: volume=0
    for attempt in range(30):
        try:
            subprocess.run(['wpctl','set-volume','@DEFAULT_AUDIO_SINK@',str(volume)],check=True,timeout=3,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            muted=bool(data.get('muted',False)) if isinstance(data,dict) else False
            subprocess.run(['wpctl','set-mute','@DEFAULT_AUDIO_SINK@','1' if muted else '0'],check=True,timeout=3,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            return
        except (OSError,subprocess.SubprocessError):
            import time
            time.sleep(1)

def collect():
    files={}
    for relative in FILES[1:]:
        path=home_path(relative)
        if path.is_file() and path.stat().st_size<=256*1024:
            try: files[relative]=filtered_file(relative,path.read_text())
            except (ValueError,configparser.Error,json.JSONDecodeError): continue
    return {'version':1,'gsettings':settings_export(),'files':files,'audio':audio_export()}

def backup(path,folder,pattern):
    if not path.is_file(): return
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(path,folder/(pattern+'-'+stamp+path.suffix))
    for old in sorted(folder.glob(pattern+'-*'+path.suffix),reverse=True)[5:]:
        if old.is_file() and not old.is_symlink(): old.unlink()

def profile_data(store):
    data=read_json(store/'settings.json')
    if not isinstance(data,dict) or data.get('version')!=1: raise ValueError('Unsupported settings profile')
    return data

@synchronized
def save():
    status,store=state()
    data=collect()
    previous=None
    try: previous=profile_data(store)
    except (OSError,ValueError): pass
    compare=lambda value: {k:v for k,v in value.items() if k!='saved_at'}
    changed=previous is None or compare(previous)!=data
    if changed:
        backup(store/'settings.json',store/'backups','settings')
        data['saved_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        atomic(store/'settings.json',json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    monitor=home_path('.config/monitors.xml')
    if monitor.is_file():
        content=monitor_xml(monitor.read_text())
        target=store/'displays'/(status['machine']+'.xml')
        if not target.exists() or target.read_text()!=content:
            backup(target,store/'backups','monitor-'+status['machine'])
            atomic(target,content)
            changed=True
    return changed

def apply_file(relative,text):
    content=filtered_file(relative,text)
    path=home_path(relative)
    base=''
    defaults=DEFAULTS/relative
    if defaults.is_file(): base=defaults.read_text()
    if relative=='.config/Code/User/settings.json':
        merged=json.loads(base or '{}');merged.update(json.loads(content))
        content=json.dumps(merged,ensure_ascii=False,indent=2)+'\n'
    else:
        merged=parse_ini(base) if base else parse_ini('')
        incoming=parse_ini(content)
        for section in incoming.sections():
            if relative=='.config/fcitx5/config' and section.startswith('Hotkey/'):
                merged.remove_section(section)
            if not merged.has_section(section): merged.add_section(section)
            for key,value in incoming.items(section): merged.set(section,key,value)
        from io import StringIO
        output=StringIO();merged.write(output,space_around_delimiters=False);content=output.getvalue()
        if relative=='.config/fcitx5/conf/hangul.conf': content=content.replace('[General]\n','',1)
    atomic(path,content)

@synchronized
def restore():
    status,store=state()
    restored=False
    try:
        data=profile_data(store)
        settings_apply(data.get('gsettings',{}))
        files=data.get('files',{})
        if isinstance(files,dict):
            for relative,text in files.items():
                if relative in FILES[1:]:
                    try: apply_file(relative,text)
                    except (ValueError,configparser.Error,json.JSONDecodeError): continue
        restored=True
    except (OSError,ValueError,json.JSONDecodeError): pass
    path=store/'displays'/(status['machine']+'.xml')
    if path.is_file() and not path.is_symlink() and path.stat().st_size<=256*1024:
        try:
            atomic(home_path('.config/monitors.xml'),monitor_xml(path.read_text()))
            restored=True
        except (ValueError,ET.ParseError): pass
    return restored

@synchronized
def reset():
    status,store=state()
    backup(store/'settings.json',store/'backups','settings')
    settings_apply({},reset=True)
    for relative in FILES[1:]:
        target=home_path(relative);default=DEFAULTS/relative
        if default.is_file(): atomic(target,default.read_text())
        else: target.unlink(missing_ok=True)
    display=store/'displays'/(status['machine']+'.xml')
    backup(display,store/'backups','monitor-'+status['machine'])
    display.unlink(missing_ok=True)
    home_path('.config/monitors.xml').unlink(missing_ok=True)
    audio_apply({'volume':0,'muted':False})
    save()

@synchronized
def rollback():
    status,store=state()
    choices=sorted((store/'backups').glob('settings-*.json'),reverse=True)
    if not choices: raise RuntimeError('No previous settings backup')
    content=choices[0].read_text()
    parsed=json.loads(content)
    if parsed.get('version')!=1: raise ValueError('Invalid backup')
    backup(store/'settings.json',store/'backups','settings')
    atomic(store/'settings.json',content)
    display=store/'displays'/(status['machine']+'.xml')
    monitors=sorted((store/'backups').glob('monitor-'+status['machine']+'-*.xml'),reverse=True)
    if monitors:
        xml=monitor_xml(monitors[0].read_text())
        backup(display,store/'backups','monitor-'+status['machine'])
        atomic(display,xml)
    restore()
    audio_apply(parsed.get('audio',{}))

def session():
    try:
        _,store=state()
        try: data=profile_data(store)
        except (OSError,ValueError): data={}
        audio_apply(data.get('audio',{}))
    except (OSError,ValueError,RuntimeError):
        audio_apply({})
        return
    stopped=threading.Event()
    for sig in (signal.SIGTERM,signal.SIGINT): signal.signal(sig,lambda *_:stopped.set())
    while not stopped.wait(30):
        try: save()
        except (OSError,ValueError,RuntimeError): pass
    try: save()
    except (OSError,ValueError,RuntimeError): pass

def panel():
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk
    try:
        status,store=state();message='USB 설정 프로필이 연결되어 있습니다.\n30초마다 변경된 설정만 저장합니다.\n저장 위치: '+str(store)
        enabled=True
    except Exception as exc: message='프로필 저장소를 사용할 수 없습니다.\n'+str(exc);enabled=False
    dialog=Gtk.MessageDialog(message_type=Gtk.MessageType.INFO,buttons=Gtk.ButtonsType.NONE,text='사용자 환경설정 프로필')
    dialog.format_secondary_text(message)
    for label,code in (('지금 저장',1),('이전 설정 복원',2),('기본값으로 초기화',3),('닫기',0)):
        button=dialog.add_button(label,code)
        if code: button.set_sensitive(enabled)
    response=dialog.run();dialog.destroy()
    if response in (2,3):
        question=Gtk.MessageDialog(message_type=Gtk.MessageType.QUESTION,buttons=Gtk.ButtonsType.YES_NO,text='이전 설정 복원' if response==2 else 'ISO 기본값으로 초기화')
        question.format_secondary_text('현재 설정은 백업됩니다. 모니터 및 실행 중인 앱 설정은 다음 로그인 때 완전히 반영됩니다.')
        answer=question.run();question.destroy()
        if answer!=Gtk.ResponseType.YES: return
    if response:
        try:
            {1:save,2:rollback,3:reset}[response]()
            text='설정을 저장했습니다.' if response==1 else '완료했습니다. 모든 설정을 반영하려면 다시 로그인하세요.'
        except Exception as exc: text='처리하지 못했습니다: '+str(exc)
        result=Gtk.MessageDialog(message_type=Gtk.MessageType.INFO,buttons=Gtk.ButtonsType.OK,text=text)
        result.run();result.destroy()

def main():
    command=sys.argv[1] if len(sys.argv)>1 else 'panel'
    actions={'save':save,'restore':restore,'reset':reset,'rollback':rollback,'session':session,'panel':panel,
             'status':lambda:print(json.dumps(read_json(STATUS),indent=2))}
    if command not in actions: raise SystemExit('Unknown profile action')
    result=actions[command]()
    if command in ('save','restore'): print(json.dumps({command+'d':bool(result)}))

if __name__=='__main__': main()
