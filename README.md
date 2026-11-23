# Portable Secure Live OS

한국어 | [English](README.en.md)

**Debian Live OS와 VeraCrypt를 이용한 USB 기반 보안 OS 프로젝트**입니다. PC에 설치하지 않고 USB에서 실행하며, 작업 파일은 암호화 저장소에 보관하고 선택한 사용자 환경설정만 다음 부팅에 복원합니다.

어디까지나 **제 개인 사용을 위해 구성한 OS**이며, 범용 배포판이나 지원을 제공하는 제품은 아닙니다. 다른 분도 아래 MIT 라이선스에 따라 사용·수정·재배포할 수 있습니다.

## 주요 기능

- Debian 13 (`trixie`) · amd64 · GNOME, Xorg 기본 세션
- 내부 저장장치의 자동 마운트 제한과 읽기 전용 정책, 디스크 swap 비활성화
- VeraCrypt 저장소의 포터블 앱 실행기를 GNOME 앱 목록에 자동 등록
- 종료·재부팅 전에 VeraCrypt 볼륨 해제 확인, 실패 시 종료 취소
- USB 프로필에 선택한 데스크톱 설정 저장, PC별 모니터 배치 구분
- Fcitx5 한글 입력과 오른쪽 Alt 한/영 전환
- GIMP · Krita · VLC · PDF/이미지 뷰어 · VS Code · Python · Node.js/nvm · Codex CLI

OS 전체 persistence는 사용하지 않습니다. 일반 세션 상태는 재부팅 후 유지하지 않고, 보존할 작업 파일은 사용자가 암호화 저장소에 저장합니다.

## 디렉터리

```text
config/                 패키지 목록, OS 기본값, 런처와 서비스 소스
  includes.chroot/       Live OS에 포함할 설정과 실행 파일
  hooks/                빌드 단계 훅
  codex/                Codex 의존성 잠금
  assets.json           외부 의존성 버전·다운로드 주소·검증 해시
scripts/                빌드 준비, 검증, 프로필 생성, 명시적 ISO 빌드
examples/               포터블 앱 실행기 예시
docs/                   빌드·사용·보안 정책 문서
.local/                 다운로드, 준비된 작업 트리, 로컬 기록 — Git 제외
build/                  ISO와 체크섬 — Git 제외
```

## 빌드 전 준비

Debian 13 또는 WSL2 Debian의 **Linux 파일시스템에 저장한 체크아웃**에서 실행합니다. 다른 사용자의 홈 경로나 Windows 드라이브 문자를 지정할 필요는 없습니다.

```bash
sudo apt update
sudo apt install live-build debootstrap squashfs-tools xorriso \
  isolinux syslinux-common grub-pc-bin grub-efi-amd64-bin mtools dosfstools python3

# 외부 패키지 준비 방법은 docs/BUILD.md 참고
python3 scripts/prepare.py
python3 scripts/validate.py --prepared
```

여기까지는 **빌드 입력 준비와 정적 검증만 수행하며 ISO를 만들지 않습니다.** VeraCrypt 패키지는 지정된 버전의 파일을 직접 준비해야 합니다. 다운로드한 바이너리와 인증 정보는 저장소에 포함하지 않습니다.

실제로 ISO를 만들 때만 다음 명령을 실행합니다.

```bash
sudo bash scripts/build.sh
```

결과는 `build/`에 저장됩니다. 상세 절차와 버전 변경 방법은 [빌드 안내](docs/BUILD.md)를 참고하세요.

## 사용과 보안 범위

- [사용 안내](docs/USAGE.md): USB 구성, 프로필, 포터블 앱, Codex 저장 위치
- [보안 정책](docs/SECURITY.md): 저장장치 보호와 종료 동작, 적용 범위
- [외부 구성요소](docs/THIRD-PARTY.md): 별도 배포 파일과 라이선스

기존 ISO에서는 VM 부팅과 주요 보호 동작을 시험했습니다. 이번 공개용 정리는 빌드 전 단계까지만 검증하며, 이 구성으로 새로 만든 ISO의 부팅·실기기 호환성은 별도 검증이 필요합니다.

## 라이선스와 면책

직접 작성한 코드·설정·문서는 [MIT 라이선스](LICENSE)로 제공합니다. 외부에서 가져온 파일과 Debian·VeraCrypt 등 구성요소는 각각의 기존 라이선스를 따릅니다. 자세한 적용 범위는 [외부 구성요소 안내](docs/THIRD-PARTY.md)를 참고하세요.

제가 쓰려고 만든 OS라서 다른 PC에서도 안전하고 문제없이 작동한다고 보장할 수는 없습니다. 다른 분도 자유롭게 사용할 수 있지만, 사용 전 중요한 자료는 백업해 주세요. 사용 중 파일이 사라지거나 PC에 문제가 생기는 등 손해가 발생해도, 법에서 정한 책임을 제외하면 제작자가 책임지지는 않습니다. 자세한 조건은 [MIT 라이선스](LICENSE)를 참고하세요.
