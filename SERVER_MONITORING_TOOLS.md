# 서버 모니터링 솔루션 가이드

개발 시 사이드로 실시간 서버 상태를 확인할 수 있는 오픈소스 솔루션 조사 결과입니다.

> 조사일: 2025-12-03

---

## 추천 솔루션 비교표

| 솔루션 | Stars | 라이선스 | 용도 | 추천 |
|--------|-------|----------|------|------|
| [Uptime Kuma](https://github.com/louislam/uptime-kuma) | ⭐ 79.2K | MIT | 서버 생존 확인 | ✅ 최우선 |
| [Netdata](https://github.com/netdata/netdata) | ⭐ 76.9K | GPL-3.0 | 시스템 리소스 분석 | 필요시 |
| [Upptime](https://github.com/upptime/upptime) | ⭐ 16.7K | MIT | 상태 페이지 (GitHub 기반) | 팀 공유용 |
| [Kener](https://github.com/rajnandan1/kener) | ⭐ 4.6K | MIT | 예쁜 상태 페이지 | 고객용 |

---

## 1. Uptime Kuma - "내 서버 살아있어?" 확인용

### 개요
웹사이트나 API 서버가 **죽었는지 살았는지** 실시간으로 감시하는 도구입니다.

### 실제 활용 예시

```
🖥️ 시나리오: archive-analyzer API 서버 개발 중

문제 상황:
- uvicorn으로 API 서버 띄워놓고 프론트엔드 작업 중
- 어느 순간 API가 죽어있는데 모르고 계속 작업
- 30분 후에야 "왜 안되지?" 발견 😤

Uptime Kuma 사용 시:
- localhost:8000/health 엔드포인트 20초마다 체크
- 서버 죽으면 즉시 Discord/Slack 알림
- "🔴 archive-analyzer DOWN" 알림 받고 바로 재시작
```

### 모니터링 가능 항목

| 타입 | 예시 |
|------|------|
| HTTP(s) | `localhost:8000/api/health`, `https://mysite.com` |
| TCP 포트 | PostgreSQL 5432, Redis 6379 열려있나? |
| Docker 컨테이너 | MeiliSearch 컨테이너 살아있나? |
| DNS | 도메인 DNS 응답하나? |
| Ping | NAS 서버 `10.10.100.122` 접속 가능한가? |

### 주요 특징
- 20초 간격 체크 (무료 서비스 대비 최고 수준)
- 95+ 알림 채널 (Discord, Slack, Telegram 등)
- 깔끔한 UI, 별도 설정 거의 불필요
- Windows 네이티브 설치 가능

### 설치 방법

```powershell
# Docker 설치 (권장)
docker run -d -p 3001:3001 -v uptime-kuma:/app/data --name uptime-kuma louislam/uptime-kuma:1

# 또는 npm으로 직접 설치
npx uptime-kuma

# 접속
# http://localhost:3001
```

### 이런 경우 추천
- ✅ 여러 서비스 동시 개발 (API + DB + 검색엔진)
- ✅ 로컬에서 Docker 컨테이너 여러 개 운영
- ✅ 서버 죽으면 바로 알고 싶을 때

---

## 2. Netdata - "왜 내 컴퓨터가 느려졌지?" 분석용

### 개요
CPU, 메모리, 디스크, 네트워크 사용량을 **1초 단위**로 실시간 그래프로 보여주는 도구입니다.

### 실제 활용 예시

```
🖥️ 시나리오: MeiliSearch 인덱싱 스크립트 실행 중

문제 상황:
- python index_to_meilisearch.py 실행했는데 엄청 느림
- 뭐가 문제인지 모름 (CPU? 메모리? 디스크?)

Netdata 사용 시:
- 대시보드 열어보니 "아, 메모리 95% 사용 중이네"
- 또는 "디스크 I/O가 100%로 병목이구나"
- 원인 파악 후 배치 크기 조절 or 메모리 확보
```

### 모니터링 가능 항목

| 항목 | 보여주는 것 |
|------|------------|
| CPU | 코어별 사용률, 어떤 프로세스가 많이 쓰나 |
| 메모리 | 사용량, 캐시, 스왑 |
| 디스크 | 읽기/쓰기 속도, IOPS |
| 네트워크 | 업로드/다운로드 속도 |
| Docker | 컨테이너별 리소스 사용량 |
| 프로세스 | Python, Node.js 등 개별 프로세스 |

### 주요 특징
- 1초 간격 실시간 수집
- ML 기반 이상 감지
- 800+ 통합 (시스템, 컨테이너, 앱)
- 제로 설정으로 바로 시작

### 설치 방법

```powershell
# Windows WSL 또는 Linux
bash <(curl -Ss https://get.netdata.cloud/kickstart.sh)

# Docker
docker run -d --name=netdata \
  -p 19999:19999 \
  -v netdataconfig:/etc/netdata \
  -v netdatalib:/var/lib/netdata \
  -v netdatacache:/var/cache/netdata \
  -v /etc/passwd:/host/etc/passwd:ro \
  -v /etc/group:/host/etc/group:ro \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  --cap-add SYS_PTRACE \
  netdata/netdata

# 접속
# http://localhost:19999
```

### 이런 경우 추천
- ✅ 무거운 작업 실행 시 병목 찾기 (인덱싱, 데이터 처리)
- ✅ "왜 갑자기 느려졌지?" 원인 분석
- ✅ Docker 컨테이너 리소스 모니터링

---

## 3. Upptime - "내 사이트 장애 기록" 공개용

### 개요
GitHub Actions가 주기적으로 사이트를 체크하고, **상태 페이지**를 자동 생성해주는 도구입니다.

### 실제 활용 예시

```
🖥️ 시나리오: 팀원/고객에게 서비스 상태 공유

문제 상황:
- "API 서버 지금 되나요?" 질문 계속 받음
- 장애 발생 시 일일이 알려줘야 함

Upptime 사용 시:
- status.myproject.com 페이지 자동 생성
- "현재 API 서버: 🟢 정상 (99.9% 가동률)"
- 장애 기록 자동 저장 및 공개
- 별도 서버 없이 GitHub Pages로 무료 호스팅
```

### 주요 특징
- GitHub Actions + GitHub Pages 활용
- 서버 비용 0원
- 상태 페이지 자동 생성
- 장애 히스토리 자동 기록

### 설치 방법
1. [upptime/upptime](https://github.com/upptime/upptime) 템플릿 사용
2. `.upptimerc.yml` 설정
3. GitHub Actions 자동 실행

### 이런 경우 추천
- ✅ 팀 프로젝트에서 상태 페이지 필요할 때
- ✅ 서버 비용 0원으로 모니터링 원할 때
- ✅ 장애 히스토리 기록/공유 필요할 때
- ❌ 로컬 개발용으로는 부적합 (외부 접근 필요)

---

## 4. Kener - "예쁜 상태 페이지" 필요할 때

### 개요
Upptime과 비슷하지만 **더 예쁜 UI**의 상태 페이지를 만들어주는 도구입니다.

### 주요 특징
- SvelteKit 기반 모던 UI
- 커스터마이징 가능한 디자인
- 다크/라이트 모드 지원

### 이런 경우 추천
- ✅ 고객/사용자에게 보여줄 공식 상태 페이지
- ✅ 브랜딩된 디자인 필요할 때

---

## 상황별 추천 정리

| 상황 | 추천 솔루션 |
|------|------------|
| **"localhost 서버들 죽으면 알려줘"** | Uptime Kuma ✅ |
| **"왜 내 스크립트가 느린지 모르겠어"** | Netdata |
| **"팀원들에게 서버 상태 공유하고 싶어"** | Upptime |
| **"고객용 예쁜 상태 페이지 필요해"** | Kener |

---

## archive-analyzer 프로젝트 모니터링 예시

현재 프로젝트 서비스 구성:

```
실행 중인 서비스들:
- uvicorn API 서버 (localhost:8000)
- Docker MeiliSearch (localhost:7700)
- Docker PostgreSQL 또는 SQLite
- NAS SMB 연결 (10.10.100.122)
```

**Uptime Kuma 모니터 설정 예시:**

| 모니터 이름 | URL/Host | 타입 | 간격 |
|------------|----------|------|------|
| Archive API | `http://localhost:8000/health` | HTTP | 30초 |
| MeiliSearch | `http://localhost:7700/health` | HTTP | 60초 |
| NAS Server | `10.10.100.122` | Ping | 60초 |

서버 하나라도 죽으면 Discord/Slack으로 즉시 알림!

---

## 참고 링크

- [Uptime Kuma - GitHub](https://github.com/louislam/uptime-kuma)
- [Netdata - GitHub](https://github.com/netdata/netdata)
- [Upptime - GitHub](https://github.com/upptime/upptime)
- [Kener - GitHub](https://github.com/rajnandan1/kener)
- [DevOpsCube - Best Open Source Monitoring Tools 2025](https://devopscube.com/best-opensource-monitoring-tools/)
- [Grafana Labs](https://grafana.com/)
- [Prometheus](https://prometheus.io/)
