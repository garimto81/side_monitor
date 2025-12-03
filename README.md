# Side Monitor

Docker 컨테이너 및 호스트 프로세스를 자동으로 감지하여 Uptime Kuma에 모니터로 등록하는 도구입니다.

## 구성

```
side_monitor/
├── README.md                      # 이 파일
├── SERVER_MONITORING_TOOLS.md     # 모니터링 솔루션 비교 가이드
├── UPTIME_KUMA_SETUP.md           # Uptime Kuma 설치 가이드
├── auto_register.py               # 자동 등록 스크립트
├── requirements.txt               # Python 의존성
├── .env                           # 환경 변수 (gitignore)
└── .env.example                   # 환경 변수 예시
```

## 빠른 시작

### 1. Uptime Kuma 설치

```powershell
docker run -d --name uptime-kuma -p 3001:3001 -v uptime-kuma:/app/data --restart unless-stopped louislam/uptime-kuma:1
```

### 2. 웹 UI 접속 및 계정 생성

```
http://localhost:3001
```

### 3. 환경 변수 설정

```powershell
cp .env.example .env
# .env 파일 수정 (KUMA_USERNAME, KUMA_PASSWORD)
```

### 4. 자동 등록 스크립트 실행

```powershell
# 의존성 설치
pip install -r requirements.txt

# Docker 컨테이너 미리보기
python auto_register.py --dry-run

# 호스트 프로세스 포함 미리보기
python auto_register.py --include-host --dry-run

# 실제 등록
python auto_register.py --include-host

# 등록된 모니터 목록 확인
python auto_register.py --list
```

## auto_register.py 기능

| 기능 | 설명 |
|------|------|
| Docker 컨테이너 자동 감지 | `docker ps`로 실행 중인 컨테이너 스캔 |
| 호스트 프로세스 감지 | Python 서버 등 직접 실행 중인 프로세스 스캔 |
| 포트 타입 자동 판단 | HTTP vs TCP 자동 구분 |
| Uptime Kuma API 연동 | 모니터 자동 등록 |
| 중복 방지 | 이미 등록된 모니터는 스킵 |
| 원격 호스트 지원 | 동일 네트워크의 다른 서버에서 모니터링 가능 |
| 라벨 필터링 | 특정 라벨의 컨테이너만 필터링 |

### CLI 옵션

| 옵션 | 설명 |
|------|------|
| `--dry-run` | 등록하지 않고 미리보기만 |
| `--list` | 현재 등록된 모니터 목록 |
| `--host <IP>` | 모니터링 대상 호스트 IP 지정 |
| `--include-host` | 호스트 프로세스도 포함 |
| `--host-only` | 호스트 프로세스만 (Docker 제외) |
| `--label <라벨>` | 라벨로 컨테이너 필터링 |
| `--watch` | 주기적 감시 모드 (데몬) |
| `--interval <초>` | 감시 주기 (기본: 300초) |

### 포트 타입 자동 판단

| 타입 | 포트 예시 |
|------|----------|
| TCP | 5432 (PostgreSQL), 3306 (MySQL), 6379 (Redis), 27017 (MongoDB) |
| HTTP | 80, 443, 3000, 5000, 8000, 8080 등 |

### 사용 예시

```powershell
# 새 컨테이너 추가 후 자동 등록
docker run -d -p 9000:9000 my-new-service
python auto_register.py
```

### 원격 호스트 모니터링

Uptime Kuma가 다른 서버(예: NAS)에서 실행 중일 때, Docker 호스트의 컨테이너를 모니터링하려면:

```powershell
# 방법 1: CLI 옵션 사용
python auto_register.py --host 192.168.1.100

# 방법 2: 환경 변수 사용 (.env 파일)
# DOCKER_HOST_IP=192.168.1.100
python auto_register.py

# 미리보기
python auto_register.py --host 192.168.1.100 --dry-run
```

**주의**: 원격 호스트 사용 시 해당 IP의 포트가 방화벽에서 열려 있어야 합니다.

## Watch 모드 (데몬)

스크립트 내장 감시 모드로 주기적으로 새로운 컨테이너/프로세스를 자동 등록합니다.

```powershell
# 기본 5분(300초) 주기로 감시
python auto_register.py --watch --include-host

# 60초 주기로 감시
python auto_register.py --watch --interval 60

# 미리보기 모드로 감시 (실제 등록 안함)
python auto_register.py --watch --dry-run

# 백그라운드 실행 (PowerShell)
Start-Process python -ArgumentList "auto_register.py --watch --include-host" -WindowStyle Hidden

# 종료: Ctrl+C (graceful shutdown)
```

**Watch 모드 특징:**
- Ctrl+C로 안전하게 종료 (현재 사이클 완료 후 종료)
- 새로운 컨테이너/프로세스만 등록 (중복 스킵)
- 오류 발생 시 다음 사이클 계속 진행

## 외부 스케줄러 사용 (대안)

OS 스케줄러를 사용한 주기적 실행도 가능합니다.

### Windows Task Scheduler

```powershell
# 5분마다 실행하는 작업 생성
$action = New-ScheduledTaskAction -Execute "python" -Argument "D:\AI\claude01\side_monitor\auto_register.py --include-host"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName "SideMonitor" -Action $action -Trigger $trigger
```

### Linux Cron

```bash
# crontab -e
*/5 * * * * cd /path/to/side_monitor && python auto_register.py --include-host
```

## 주의사항

- `.env` 파일에 비밀번호가 포함되어 있으므로 `.gitignore`에 추가 권장
- 중복 모니터는 자동으로 스킵됨
- Uptime Kuma는 단일 인스턴스로 운영 (클러스터링 미지원)

## 트러블슈팅

### Windows port proxy 문제

외부에서 접속이 안 되는 경우 port proxy 규칙 확인:

```powershell
# port proxy 규칙 확인
netsh interface portproxy show all

# 문제가 있는 규칙 삭제
netsh interface portproxy delete v4tov4 listenport=3001 listenaddress=0.0.0.0
```

## 문서

- [서버 모니터링 솔루션 비교](SERVER_MONITORING_TOOLS.md)
- [Uptime Kuma 설치 가이드](UPTIME_KUMA_SETUP.md)
