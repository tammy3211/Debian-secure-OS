# Portable Secure Live OS

[한국어](README.md) | English

A **USB-based security OS project built with Debian Live OS and VeraCrypt**. It boots from USB without installation on the host PC, keeps work files in encrypted storage, and restores selected user preferences on the next boot.

This OS is configured **primarily for my own personal use**. It is not a general-purpose distribution or a supported product. Others are welcome to use, modify, and redistribute the original project materials under the MIT License.

## Features

- Debian 13 (`trixie`), amd64, GNOME, with Xorg as the default session
- Restrictions on automatic mounting of internal storage, read-only policies, and disabled disk swap
- Automatic registration of portable application launchers from VeraCrypt storage in the GNOME application list
- VeraCrypt dismount checks before shutdown or reboot; shutdown is cancelled if dismounting fails
- Selected desktop preferences stored in a USB profile, with separate monitor layouts for each machine
- Fcitx5 Korean input and Right Alt for Korean/English switching
- GIMP, Krita, VLC, PDF/image viewers, VS Code, Python, Node.js/nvm, and Codex CLI

Full OS persistence is not enabled. Ordinary session state does not survive reboot. Save work files that you want to keep in encrypted storage.

## Repository layout

```text
config/                 Package lists, OS defaults, launcher and service sources
  includes.chroot/       Configuration and executables included in the Live OS
  hooks/                Build-stage hooks
  codex/                Locked Codex dependencies
  assets.json           External dependency versions, URLs, and verification hashes
scripts/                Preparation, validation, profile creation, and explicit ISO build
examples/               Example portable application launcher
docs/                   Build, usage, and security documentation
.local/                 Downloads, prepared trees, and local records; excluded from Git
build/                  ISO images and checksums; excluded from Git
```

## Prepare the build inputs

Use a checkout stored on the **Linux filesystem** of Debian 13 or WSL2 Debian. No machine-specific home directory or Windows drive letter is required.

```bash
sudo apt update
sudo apt install live-build debootstrap squashfs-tools xorriso \
  isolinux syslinux-common grub-pc-bin grub-efi-amd64-bin mtools dosfstools python3

# See docs/BUILD.md for external package preparation.
python3 scripts/prepare.py
python3 scripts/validate.py --prepared
```

These steps **prepare and statically validate build inputs without creating an ISO**. Obtain the pinned VeraCrypt package separately. Downloaded binaries and credentials are not included in the repository.

Run the following command only when you want to build an ISO:

```bash
sudo bash scripts/build.sh
```

Results are saved in `build/`. See the [build guide](docs/BUILD.md) for details and dependency update instructions.

## Usage and security scope

- [Usage](docs/USAGE.md): USB layout, preferences, portable applications, and Codex storage
- [Security scope](docs/SECURITY.md): storage protection, shutdown behavior, and limitations
- [Third-party components](docs/THIRD-PARTY.md): external distributions and licensing

Earlier ISO images were tested for VM boot and key protection behavior. This public source configuration has been validated only through the preparation stage. Newly built images still require boot testing and hardware compatibility checks.

## License and disclaimer

Original code, configuration, and documentation are provided under the [MIT License](LICENSE). Upstream-derived files and components such as Debian and VeraCrypt retain their own licenses. See [third-party licensing](docs/THIRD-PARTY.md) for the scope.

I made this OS for my own use, so I cannot promise that it will work safely or without problems on other PCs. You are welcome to use it, but please back up important files first. Except where applicable law requires otherwise, the author is not responsible for lost files, system damage, or other losses caused by using this project. See the [MIT License](LICENSE) for the full terms.
