# Usage

This is an OS configuration made primarily for the maintainer's personal use. Others may use, modify, and redistribute the original project materials under the [MIT License](../LICENSE). It is provided as-is, without a commitment to maintenance, support, or compatibility with other machines. See [security scope and disclaimer](SECURITY.md).

## USB layout

Boot the Live ISO using Ventoy or another suitable boot method. Store work files in a separate VeraCrypt file container. Windows drive letters are not Linux paths. Users manage their own VeraCrypt passwords and container files.

```text
USB/
  OS/portable-live-os.iso
  LiveProfile/                 Selected ordinary preferences
  Workspace.hc                 Example encrypted VeraCrypt container
```

## Desktop defaults

The defaults include Right Alt for Korean/English input switching, slightly reduced mouse sensitivity, disabled automatic suspend, screen blanking after ten idle minutes, and an initial output volume of zero. The power button action is `interactive`: on an ordinary PC with an unlocked, responsive GNOME session, a short press opens the shutdown confirmation dialog.

## User preferences

After preparing the build inputs, create a new profile directory:

```bash
python3 scripts/init-profile.py .local/LiveProfile
```

Copy the generated `LiveProfile/` directory to the root of the Ventoy USB. The profile stores selected display, input, audio, and allowlisted application preferences. It does not persist the entire home directory, browser history, or credentials. Monitor layouts are separated by machine. Ordinary profiles are not encrypted; do not put secrets in them.

Use the user preferences profile application or `live-profile status`, `live-profile save`, `live-profile rollback`, and `live-profile reset`. The store identifier must match the ISO configuration. The helper does not automatically select an arbitrary external storage device.

## VeraCrypt portable applications

Mount the volume at a default path between `/media/veracrypt1` and `/media/veracrypt64`. Keep application files in the encrypted volume:

```text
APP/
  MyApp.desktop
  MyApp/start.sh
  MyApp/icon.png
  MyApp/data/
```

The helper registers `APP/*.desktop` entries in the GNOME application list after mounting. Registration does not launch an application. Entries are removed when the volume is dismounted. In the [launcher example](../examples/MyApp.desktop), the project helper replaces `@VC_MOUNT@` with the actual mount path.

The default exFAT mount options are `exec,uid=1000,gid=1000,fmask=0022,dmask=0022,nosuid,nodev`. Use appropriate options for other filesystem types.

## Codex CLI

Run `codex` in a terminal. The `/usr/local/bin/codex` wrapper prints the selected storage location when starting.

- With one mounted VeraCrypt volume, it uses `APP/Codex/state` on that volume.
- With multiple volumes, it selects the one containing the only `APP/Codex` directory. Ambiguous selection stops startup.
- With no matching mount, it uses `/run/user/1000/codex-live`, which does not survive reboot.
- An unwritable selected encrypted store causes an error.

Configuration, credentials, ordinary caches, and logs are stored beneath the selected directory. Because exFAT cannot create the required helper links, only `state/tmp` is connected to a RAM directory. Storage is selected when the process starts; mount the volume before launching Codex.

Check command resolution with `type -a codex` and authentication with `codex login status`. Use `codex login` to sign in. Do not copy credentials into the ordinary USB profile or Git repository. Earlier tests verified temporary API-key storage and removal; actual account login still needs separate verification.
