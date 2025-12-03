# Side Monitor

개발 중 실시간 서버 상태를 모니터링하기 위한 도구 모음입니다.

## 구성

```
side_monitor/
├── README.md                      # 이 파일
├── SERVER_MONITORING_TOOLS.md     # 모니터링 솔루션 비교 가이드
├── UPTIME_KUMA_SETUP.md           # Uptime Kuma 설치 가이드
├── auto_register.py               # Docker 컨테이너 자동 등록 스크립트
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
pip install uptime-kuma-api python-dotenv

# 실행 중인 Docker 컨테이너 미리보기 (등록 안함)
python auto_register.py --dry-run

# 실제 등록
python auto_register.py

# 등록된 모니터 목록 확인
python auto_register.py --list
```

## auto_register.py 기능

| 기능 | 설명 |
|------|------|
| Docker 컨테이너 자동 감지 | `docker ps`로 실행 중인 컨테이너 스캔 |
| 포트 타입 자동 판단 | HTTP vs TCP 자동 구분 |
| Uptime Kuma API 연동 | 모니터 자동 등록 |
| 중복 방지 | 이미 등록된 모니터는 스킵 |
| 원격 호스트 지원 | 동일 네트워크의 다른 서버에서 모니터링 가능 |

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

## 주의사항

- `.env` 파일에 비밀번호가 포함되어 있으므로 `.gitignore`에 추가 권장
- 스크립트는 1회성 실행, 주기적 실행이 필요하면 Task Scheduler 사용
- Uptime Kuma는 단일 인스턴스로 운영 (클러스터링 미지원)

## 문서

- [서버 모니터링 솔루션 비교](SERVER_MONITORING_TOOLS.md)
- [Uptime Kuma 설치 가이드](UPTIME_KUMA_SETUP.md)
