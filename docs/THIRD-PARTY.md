# Licensing and third-party components

## Original project materials

Original code, configuration, examples, and documentation authored for this project are licensed under the [MIT License](../LICENSE). The copyright notice uses the maintainer's Git identity, `tom020723`.

This is primarily a personal OS configuration. Others may use, modify, and redistribute its original materials, including commercially, subject to the MIT terms. The personal-use description is not a noncommercial or personal-use-only restriction. The project is provided as-is; see the license and [disclaimer](SECURITY.md#no-warranty-limitation-of-liability).

## Scope and exceptions

The root MIT License does not relicense Debian, downloaded dependencies, upstream-derived files, or a complete built ISO. Existing third-party copyright notices and license terms remain applicable. If a file contains or derives from upstream material, preserve the upstream terms and required attribution rather than treating the entire file as original MIT-licensed work.

| Component | Licensing information |
| --- | --- |
| Debian packages, GNOME, applications, and firmware | Each package's license; inspect `/usr/share/doc/<package>/copyright` in the built system. |
| VeraCrypt | The license and notices included with the selected official release. |
| VS Code distribution and editor extensions | Their respective distribution terms and extension licenses. |
| Node.js and bundled dependencies | The license and third-party notices included in the selected release. |
| nvm | The license included in the selected upstream archive. |
| Codex CLI and platform package | The licenses and notices included in the pinned npm packages. |
| Additional applications | Their own licenses and redistribution terms. |

This table identifies where to verify terms; it is not a completed license audit of every transitive dependency.

## Source repository and ISO distribution

The public repository contains project sources and dependency versions, hashes, and lockfiles. Third-party installers, executable bundles, editor extension installations, and ISO files are excluded from Git. Local artifacts remain under `.local/` or `build/`.

Before redistributing an ISO, review the licenses of the exact included package versions, retain their required notices, and satisfy any corresponding-source or other redistribution obligations. A top-level MIT License alone does not satisfy the obligations of every bundled component.
