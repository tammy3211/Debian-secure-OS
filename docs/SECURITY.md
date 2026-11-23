# Security scope and disclaimer

## Personal-use project

This OS configuration was created for the maintainer's own use. It is not a general-purpose distribution or a supported security product. Other users are welcome to use and adapt the original project materials under the [MIT License](../LICENSE). Personal-use intent does not restrict the permissions granted by that license.

## Storage devices

Internal storage is classified in initramfs and udev, with read-only policies and polkit mount restrictions. USB devices and VeraCrypt mappings are treated separately as work storage. `swap.target` is masked and the boot command line includes `noswap`.

Classification uses bus topology and removable-device information. Verify the policy on each target machine, especially when NVMe, SATA, and USB configurations differ.

## Shutdown protection

Selecting Power Off or Restart in GNOME's confirmation dialog asks a root service to save selected preferences, synchronize writes, clean up Codex runtime bindings, and attempt normal VeraCrypt dismounts. If encrypted devices remain, shutdown is cancelled and the desktop session stays available.

Ordinary `poweroff`, `reboot`, `shutdown now`, and `systemctl poweroff/reboot` commands use the same service. Explicit administrative bypasses through original binaries, forced power removal, power failures, and a completely frozen OS are outside this protection. The service does not save unsaved application documents.

The GNOME extension targets GNOME 48. Retest VM and physical hardware behavior after changing GNOME versions or shutdown paths. VM power-button handling can differ from an ordinary PC.

## Persistence and trust

The ordinary USB profile restores allowlisted preferences only. Work files and credentials belong in a separate VeraCrypt store. Passwords are not embedded in the ISO. Only use application launchers from encrypted storage when you trust their contents.

The project aims to restrict internal-disk writes and provide an encrypted workspace. It does not guarantee anonymity, the absence of recoverable traces, or identical protection on every device.

## No warranty; limitation of liability

The project is provided **AS IS**, without warranties of security, reliability, compatibility, merchantability, fitness for a particular purpose, or noninfringement. Users are responsible for deciding whether it is suitable for their environment.

To the extent permitted by applicable law, the authors and copyright holders are not liable for data loss, system damage, or other claims or losses arising from use of the project. The full warranty disclaimer and limitation of liability are in the [MIT License](../LICENSE). This explanation adds no restrictions to that license and does not replace third-party license terms.
