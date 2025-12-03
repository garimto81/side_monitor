# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Docker 컨테이너를 자동으로 감지하여 Uptime Kuma에 모니터로 등록하는 도구입니다.

## Commands

```powershell
# 의존성 설치
pip install uptime-kuma-api python-dotenv

# Docker 컨테이너 스캔 (등록 없이 미리보기)
python D:\AI\claude01\side_monitor\auto_register.py --dry-run

# 실제 Uptime Kuma에 모니터 등록
python D:\AI\claude01\side_monitor\auto_register.py

# 원격 호스트 지정 (동일 네트워크에서 모니터링)
python D:\AI\claude01\side_monitor\auto_register.py --host 192.168.1.100

# 등록된 모니터 목록 확인
python D:\AI\claude01\side_monitor\auto_register.py --list
```

## Architecture

```
auto_register.py
├── get_docker_containers()     # docker ps 실행 → ContainerInfo 리스트
├── parse_ports()               # Docker 포트 문자열 파싱
├── generate_monitor_config()   # 포트 타입에 따라 HTTP/TCP 모니터 설정 생성
├── register_monitors_via_api() # uptime-kuma-api로 실제 등록
└── list_existing_monitors()    # 현재 등록된 모니터 조회
```

### Port Type Detection

| 포트 | 타입 | 예시 |
|------|------|------|
| 5432, 3306, 27017, 6379 등 | TCP | PostgreSQL, MySQL, MongoDB, Redis |
| 80, 443, 3000, 8000, 8080 등 | HTTP | 웹 서비스 |
| 3000 이상 기타 | HTTP | 커스텀 웹 서비스 |

컨테이너 이름에 `api` 또는 `backend` 포함 시 `/health` 엔드포인트 자동 추가.

## Environment Variables

`.env.example`을 `.env`로 복사 후 설정:

| 변수 | 용도 |
|------|------|
| `KUMA_URL` | Uptime Kuma URL (기본: `http://localhost:3001`) |
| `KUMA_USERNAME` | 로그인 사용자명 |
| `KUMA_PASSWORD` | 로그인 비밀번호 |
| `DOCKER_HOST_IP` | Docker 호스트 IP (원격 모니터링용, 기본: `localhost`) |
