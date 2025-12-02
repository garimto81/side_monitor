# Uptime Kuma 설치 및 실행 가이드

Uptime Kuma는 가벼운 self-hosted 모니터링 도구로, 서버/서비스의 가동 상태를 실시간으로 확인할 수 있습니다.

> 작성일: 2025-12-03

---

## 목차

1. [시스템 요구사항](#시스템-요구사항)
2. [설치 방법](#설치-방법)
3. [초기 설정](#초기-설정)
4. [모니터 추가](#모니터-추가)
5. [알림 설정](#알림-설정)
6. [유용한 팁](#유용한-팁)
7. [트러블슈팅](#트러블슈팅)

---

## 시스템 요구사항

| 항목 | 최소 요구사항 |
|------|--------------|
| OS | Windows 10/11, Linux, macOS |
| Node.js | 18+ (npm 설치 시) |
| Docker | 20.10+ (Docker 설치 시) |
| 메모리 | 256MB+ |
| 디스크 | 1GB+ |

---

## 설치 방법

### 방법 1: Docker (권장)

가장 간단하고 권장되는 방법입니다.

```powershell
# 기본 설치
docker run -d `
  --name uptime-kuma `
  -p 3001:3001 `
  -v uptime-kuma:/app/data `
  --restart unless-stopped `
  louislam/uptime-kuma:1

# 설치 확인
docker ps | findstr uptime-kuma
```

**Docker Compose 사용 시:**

```yaml
# docker-compose.yml
version: '3.8'

services:
  uptime-kuma:
    image: louislam/uptime-kuma:1
    container_name: uptime-kuma
    ports:
      - "3001:3001"
    volumes:
      - uptime-kuma-data:/app/data
    restart: unless-stopped

volumes:
  uptime-kuma-data:
```

```powershell
# 실행
docker-compose up -d
```

---

### 방법 2: npm (Node.js 직접 설치)

Node.js가 설치되어 있다면 npm으로 직접 설치할 수 있습니다.

```powershell
# 설치 디렉토리 생성
mkdir D:\tools\uptime-kuma
cd D:\tools\uptime-kuma

# 설치
npm install uptime-kuma

# 실행
npx uptime-kuma

# 또는 전역 설치
npm install -g uptime-kuma
uptime-kuma
```

---

### 방법 3: Git Clone (개발/커스텀용)

```powershell
# 클론
git clone https://github.com/louislam/uptime-kuma.git
cd uptime-kuma

# 의존성 설치
npm run setup

# 실행 (프로덕션)
npm run start-server

# 실행 (개발)
npm run dev
```

---

## 초기 설정

### 1. 웹 UI 접속

설치 후 브라우저에서 접속:

```
http://localhost:3001
```

### 2. 관리자 계정 생성

첫 접속 시 관리자 계정을 생성합니다:

| 항목 | 권장값 |
|------|--------|
| Username | admin |
| Password | 안전한 비밀번호 (12자 이상) |

### 3. 언어 설정

- Settings → General → Language → **한국어** 선택

---

## 모니터 추가

### HTTP(s) 모니터 (API 서버 체크)

1. **Add New Monitor** 클릭
2. 설정:
   - Monitor Type: `HTTP(s)`
   - Friendly Name: `Archive API`
   - URL: `http://localhost:8000/health`
   - Heartbeat Interval: `30` (초)
   - Retries: `3`

### TCP 포트 모니터 (DB 연결 체크)

1. Monitor Type: `TCP Port`
2. 설정:
   - Friendly Name: `PostgreSQL`
   - Hostname: `localhost`
   - Port: `5432`
   - Heartbeat Interval: `60`

### Ping 모니터 (서버 접속 체크)

1. Monitor Type: `Ping`
2. 설정:
   - Friendly Name: `NAS Server`
   - Hostname: `10.10.100.122`
   - Heartbeat Interval: `60`

### Docker 컨테이너 모니터

1. Monitor Type: `Docker Container`
2. 설정:
   - Friendly Name: `MeiliSearch`
   - Container Name/ID: `meilisearch`
   - Docker Host: 기본값

---

## 알림 설정

### Discord 알림

1. **Settings → Notifications → Setup Notification**
2. Notification Type: `Discord`
3. Discord Webhook URL 입력:
   ```
   https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
   ```
4. **Test** 버튼으로 확인

**Discord Webhook 생성 방법:**
1. Discord 서버 → 채널 설정 → 연동
2. 웹후크 → 새 웹후크 → URL 복사

### Slack 알림

1. Notification Type: `Slack`
2. Webhook URL 입력
3. Channel (선택): `#monitoring`

### Telegram 알림

1. Notification Type: `Telegram`
2. Bot Token: BotFather에서 생성
3. Chat ID: 본인 또는 그룹 ID

---

## 권장 모니터 설정 (archive-analyzer 프로젝트)

| 모니터 이름 | 타입 | URL/Host | 간격 | 설명 |
|------------|------|----------|------|------|
| Archive API | HTTP(s) | `http://localhost:8000/health` | 30초 | FastAPI 서버 |
| MeiliSearch | HTTP(s) | `http://localhost:7700/health` | 60초 | 검색 엔진 |
| NAS Server | Ping | `10.10.100.122` | 60초 | 파일 서버 |
| PostgreSQL | TCP | `localhost:5432` | 60초 | 데이터베이스 |

---

## 유용한 팁

### 1. 상태 페이지 공개

- Status Pages → Add Status Page
- 팀원과 공유할 수 있는 공개 상태 페이지 생성

### 2. 유지보수 모드

서버 점검 시:
- 모니터 → 점검 모드 → Maintenance 설정
- 알림 없이 일시 중지

### 3. 인증서 만료 알림

HTTPS 모니터 추가 시:
- Certificate Expiry Notification: `ON`
- 만료 30일 전 알림 수신

### 4. 백업

```powershell
# Docker 볼륨 백업
docker run --rm -v uptime-kuma:/data -v ${PWD}:/backup alpine tar czf /backup/uptime-kuma-backup.tar.gz /data

# 복원
docker run --rm -v uptime-kuma:/data -v ${PWD}:/backup alpine tar xzf /backup/uptime-kuma-backup.tar.gz -C /
```

---

## 트러블슈팅

### Docker 컨테이너가 시작되지 않음

```powershell
# 로그 확인
docker logs uptime-kuma

# 컨테이너 재시작
docker restart uptime-kuma
```

### 포트 충돌

```powershell
# 3001 포트 사용 중인 프로세스 확인
netstat -ano | findstr :3001

# 다른 포트로 실행
docker run -d -p 3002:3001 -v uptime-kuma:/app/data --name uptime-kuma louislam/uptime-kuma:1
```

### 데이터 초기화

```powershell
# 컨테이너 삭제
docker rm -f uptime-kuma

# 볼륨 삭제 (주의: 모든 데이터 삭제)
docker volume rm uptime-kuma

# 재설치
docker run -d -p 3001:3001 -v uptime-kuma:/app/data --name uptime-kuma louislam/uptime-kuma:1
```

### Windows 방화벽 문제

```powershell
# 방화벽에서 포트 허용
netsh advfirewall firewall add rule name="Uptime Kuma" dir=in action=allow protocol=TCP localport=3001
```

---

## 서비스 관리

### 시작/중지/재시작

```powershell
# Docker
docker start uptime-kuma
docker stop uptime-kuma
docker restart uptime-kuma

# 상태 확인
docker ps -a | findstr uptime-kuma
```

### 업데이트

```powershell
# Docker 이미지 업데이트
docker pull louislam/uptime-kuma:1
docker rm -f uptime-kuma
docker run -d -p 3001:3001 -v uptime-kuma:/app/data --name uptime-kuma louislam/uptime-kuma:1
```

---

## 참고 링크

- [Uptime Kuma GitHub](https://github.com/louislam/uptime-kuma)
- [공식 문서](https://github.com/louislam/uptime-kuma/wiki)
- [Docker Hub](https://hub.docker.com/r/louislam/uptime-kuma)
