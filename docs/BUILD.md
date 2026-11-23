# Build guide

## Environment

Use Debian 13 amd64 or WSL2 Debian. Keep the checkout on the Linux filesystem, preferably under your Linux home directory. Preparation requires Python 3.12 or later and `live-build`. Building the ISO requires root privileges and an internet connection.

Install the prerequisites listed in the [README](../README.md), then follow the steps below. Preparation does not modify the host's `/etc` or reuse an existing WSL build directory.

## External dependencies

`config/assets.json` pins asset versions, filenames, and SHA-256 hashes. Preparation downloads Node.js, nvm, and VS Code from the specified URLs and verifies their contents. Codex and its Linux x64 binary are pinned by `config/codex/package-lock.json` and verified against npm integrity values. Dependencies are not automatically upgraded.

Obtain the Debian 13 amd64 VeraCrypt package from the [official download page](https://veracrypt.io/en/Downloads.html) and place it at:

```text
.local/downloads/veracrypt_1.26.31-1~deb13-1_amd64.deb
```

Renaming a different package does not satisfy verification: its SHA-256 must match the manifest. If the pinned version is no longer available, verify the replacement's official signature and checksums before explicitly updating the manifest. This repository does not redistribute third-party binaries.

Existing cached dependencies are verified and reused.

```bash
python3 scripts/prepare.py
python3 scripts/validate.py --prepared
```

Use `prepare.py --offline` when every required download is already cached. Running `validate.py` without `--prepared` checks public source syntax without downloading dependencies.

## Prepared tree

Preparation creates `.local/prepared/` with live-build configuration, verified dependencies, and symbolic links. It also sets Linux executable permissions and normalizes line endings. A fresh USB profile identifier is stored in `.local/profile-id`; personal profiles are not included in the source tree.

After editing configuration, move the previous `.local/prepared/` aside and prepare again. Existing prepared trees are never automatically overwritten or deleted. The build entry point compares a source fingerprint to prevent building from stale configuration.

## Build the ISO

```bash
sudo bash scripts/build.sh
```

Only this command invokes `lb build`. Working files remain in `.local/prepared/`, logs in `.local/build.log`, and the resulting ISO and SHA-256 file in `build/`. Allow at least several tens of GiB of free storage. Failed working trees are retained for inspection.

APT packages use the Debian repository versions available at build time. Pinned configuration and external assets therefore do not guarantee a byte-for-byte reproduction of an earlier ISO.

## Additional applications and editor extensions

PeaZip binaries and installed VS Code extension directories from earlier local images are not copied into the public source tree. The public default recipe does not include those binary bundles. To add them, review their origin, version, and licensing, prepare them separately, and test the resulting ISO.

## Publishing source

`.gitignore` excludes local caches, ISOs, virtual disks, authentication files, and encrypted containers. Earlier diagnostic records and device-specific profiles are retained locally under `.local/legacy/`. Do not upload `.local/` or `build/` through GitHub's web upload interface.

Remote configuration, commits, and pushes are separate actions. Preparation does not publish files to GitHub. See [third-party licensing](THIRD-PARTY.md) before distributing a complete ISO.
