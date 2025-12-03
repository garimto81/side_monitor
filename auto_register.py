"""
Docker 컨테이너 자동 감지 및 Uptime Kuma 모니터 등록 스크립트

사용법:
    python auto_register.py              # 실행 중인 컨테이너 스캔 및 등록
    python auto_register.py --dry-run    # 등록하지 않고 미리보기만
    python auto_register.py --list       # 현재 등록된 모니터 목록
"""

import subprocess
import json
import asyncio
import argparse
import re
from dataclasses import dataclass
from typing import Optional
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Uptime Kuma 설정
KUMA_URL = os.getenv("KUMA_URL", "http://localhost:3001")
KUMA_USERNAME = os.getenv("KUMA_USERNAME", "")
KUMA_PASSWORD = os.getenv("KUMA_PASSWORD", "")

# Docker 호스트 설정 (원격 모니터링용)
DOCKER_HOST_IP = os.getenv("DOCKER_HOST_IP", "localhost")


@dataclass
class ContainerInfo:
    """Docker 컨테이너 정보"""
    name: str
    image: str
    ports: list[dict]
    status: str
    health: Optional[str] = None


def get_docker_containers() -> list[ContainerInfo]:
    """실행 중인 Docker 컨테이너 목록 조회"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="replace"
        )

        containers = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            data = json.loads(line)

            # 포트 파싱
            ports = parse_ports(data.get("Ports", ""))

            # health 상태 추출
            status = data.get("Status", "")
            health = None
            if "(healthy)" in status:
                health = "healthy"
            elif "(unhealthy)" in status:
                health = "unhealthy"
            elif "(health:" in status:
                health = "starting"

            containers.append(ContainerInfo(
                name=data.get("Names", ""),
                image=data.get("Image", ""),
                ports=ports,
                status=status,
                health=health
            ))

        return containers
    except subprocess.CalledProcessError as e:
        print(f"Error running docker ps: {e}")
        return []


def parse_ports(ports_str: str) -> list[dict]:
    """Docker 포트 문자열 파싱

    예시: "0.0.0.0:8000->8000/tcp, :::8000->8000/tcp"
    """
    ports = []
    if not ports_str:
        return ports

    # 패턴: host_ip:host_port->container_port/protocol
    pattern = r"(?:(\d+\.\d+\.\d+\.\d+):)?(\d+)->(\d+)/(\w+)"

    for match in re.finditer(pattern, ports_str):
        host_ip = match.group(1) or "0.0.0.0"
        host_port = int(match.group(2))
        container_port = int(match.group(3))
        protocol = match.group(4)

        # 중복 제거 (IPv4만)
        port_info = {
            "host_ip": host_ip,
            "host_port": host_port,
            "container_port": container_port,
            "protocol": protocol
        }
        if port_info not in ports:
            ports.append(port_info)

    return ports


def generate_monitor_config(container: ContainerInfo, host: str = None) -> list[dict]:
    """컨테이너 정보로 모니터 설정 생성

    Args:
        container: Docker 컨테이너 정보
        host: 모니터링 대상 호스트 (기본값: DOCKER_HOST_IP 환경변수 또는 localhost)
    """
    monitors = []
    target_host = host or DOCKER_HOST_IP

    # TCP 전용 포트 (데이터베이스, 캐시 등)
    tcp_only_ports = [5432, 3306, 27017, 6379, 5379, 11211, 9042]

    # HTTP 서비스로 추정되는 포트
    http_ports = [80, 443, 3000, 3001, 4000, 5000, 5001, 8000, 8080, 8096, 8443, 9000, 8920]

    for port in container.ports:
        if port["protocol"] != "tcp":
            continue

        host_port = port["host_port"]

        # TCP 전용 포트는 TCP 모니터로
        if host_port in tcp_only_ports:
            monitors.append({
                "type": "port",
                "name": f"{container.name}:{host_port} (TCP)",
                "hostname": target_host,
                "port": host_port,
                "interval": 60,
                "retryInterval": 60,
                "maxretries": 3,
            })
        elif host_port in http_ports or host_port >= 3000:
            # HTTP 모니터
            monitor = {
                "type": "http",
                "name": f"{container.name}:{host_port}",
                "url": f"http://{target_host}:{host_port}",
                "method": "GET",
                "interval": 60,
                "retryInterval": 60,
                "maxretries": 3,
                "accepted_statuscodes": ["200-299", "300-399"],
            }

            # health 엔드포인트 추가 시도
            if "api" in container.name.lower() or "backend" in container.name.lower():
                monitor["url"] = f"http://{target_host}:{host_port}/health"

            monitors.append(monitor)
        else:
            # 기타 포트는 TCP 모니터
            monitors.append({
                "type": "port",
                "name": f"{container.name}:{host_port} (TCP)",
                "hostname": target_host,
                "port": host_port,
                "interval": 60,
                "retryInterval": 60,
                "maxretries": 3,
            })

    return monitors


def print_container_summary(containers: list[ContainerInfo]):
    """컨테이너 요약 출력"""
    print("\n" + "=" * 60)
    print("Running Docker Containers")
    print("=" * 60)

    for c in containers:
        health_icon = {
            "healthy": "[OK]",
            "unhealthy": "[FAIL]",
            "starting": "[...]",
            None: "[--]"
        }.get(c.health, "[--]")

        print(f"\n{health_icon} {c.name}")
        print(f"   Image: {c.image}")
        print(f"   Status: {c.status}")

        if c.ports:
            ports_str = ", ".join([f"{p['host_port']}" for p in c.ports])
            print(f"   Ports: {ports_str}")


def print_monitors_to_create(monitors: list[dict]):
    """생성할 모니터 목록 출력"""
    print("\n" + "=" * 60)
    print("Monitors to Create in Uptime Kuma")
    print("=" * 60)

    for m in monitors:
        type_icon = "[HTTP]" if m["type"] == "http" else "[TCP]"
        url = m.get("url") or f"{m.get('hostname')}:{m.get('port')}"
        print(f"\n{type_icon} {m['name']}")
        print(f"   Type: {m['type'].upper()}")
        print(f"   URL: {url}")
        print(f"   Interval: {m['interval']}s")


async def register_monitors_via_api(monitors: list[dict]):
    """Uptime Kuma API로 모니터 등록 (uptime-kuma-api 라이브러리 사용)"""
    try:
        from uptime_kuma_api import UptimeKumaApi, MonitorType

        api = UptimeKumaApi(KUMA_URL)
        api.login(KUMA_USERNAME, KUMA_PASSWORD)

        # 기존 모니터 목록 조회
        existing = api.get_monitors()
        existing_names = {m["name"] for m in existing}

        created = 0
        skipped = 0

        for m in monitors:
            if m["name"] in existing_names:
                print(f"[SKIP] Already exists: {m['name']}")
                skipped += 1
                continue

            try:
                if m["type"] == "http":
                    api.add_monitor(
                        type=MonitorType.HTTP,
                        name=m["name"],
                        url=m["url"],
                        method=m.get("method", "GET"),
                        interval=m["interval"],
                        retryInterval=m.get("retryInterval", 60),
                        maxretries=m.get("maxretries", 3),
                        accepted_statuscodes=m.get("accepted_statuscodes", ["200-299"]),
                    )
                else:
                    api.add_monitor(
                        type=MonitorType.PORT,
                        name=m["name"],
                        hostname=m["hostname"],
                        port=m["port"],
                        interval=m["interval"],
                        retryInterval=m.get("retryInterval", 60),
                        maxretries=m.get("maxretries", 3),
                    )
                print(f"[OK] Created: {m['name']}")
                created += 1
            except Exception as e:
                print(f"[FAIL] {m['name']} - {e}")

        api.disconnect()

        print(f"\nResult: {created} created, {skipped} skipped")

    except ImportError:
        print("\n[WARN] uptime-kuma-api library required.")
        print("   Install: pip install uptime-kuma-api")
        print("\nManually add monitors in Uptime Kuma:")
        print(f"   URL: {KUMA_URL}")


async def list_existing_monitors():
    """기존 모니터 목록 출력"""
    try:
        from uptime_kuma_api import UptimeKumaApi

        api = UptimeKumaApi(KUMA_URL)
        api.login(KUMA_USERNAME, KUMA_PASSWORD)

        monitors = api.get_monitors()

        print("\n" + "=" * 60)
        print(f"Uptime Kuma Registered Monitors ({len(monitors)})")
        print("=" * 60)

        for m in monitors:
            status_icon = "[ON]" if m.get("active") else "[OFF]"
            print(f"\n{status_icon} {m['name']}")
            print(f"   Type: {m['type']}")
            if m.get("url"):
                print(f"   URL: {m['url']}")
            if m.get("hostname"):
                print(f"   Host: {m['hostname']}:{m.get('port', '')}")

        api.disconnect()

    except ImportError:
        print("[WARN] uptime-kuma-api library required.")
        print("   Install: pip install uptime-kuma-api")


def main():
    parser = argparse.ArgumentParser(description="Docker 컨테이너 자동 Uptime Kuma 등록")
    parser.add_argument("--dry-run", action="store_true", help="등록하지 않고 미리보기만")
    parser.add_argument("--list", action="store_true", help="현재 등록된 모니터 목록")
    parser.add_argument("--host", type=str, default=None,
                        help="Docker 호스트 IP/hostname (기본: DOCKER_HOST_IP 환경변수 또는 localhost)")
    args = parser.parse_args()

    if args.list:
        asyncio.run(list_existing_monitors())
        return

    # Docker 컨테이너 조회
    containers = get_docker_containers()

    if not containers:
        print("No running Docker containers found.")
        return

    # 컨테이너 요약 출력
    print_container_summary(containers)

    # 대상 호스트 결정
    target_host = args.host or DOCKER_HOST_IP
    print(f"\nTarget host: {target_host}")

    # 모니터 설정 생성
    all_monitors = []
    for c in containers:
        monitors = generate_monitor_config(c, host=target_host)
        all_monitors.extend(monitors)

    if not all_monitors:
        print("\nNo ports to monitor.")
        return

    # 생성할 모니터 출력
    print_monitors_to_create(all_monitors)

    # 등록
    if args.dry_run:
        print("\n[DRY-RUN] No actual registration performed.")
    else:
        print("\n" + "=" * 60)
        print("Registering monitors to Uptime Kuma...")
        print("=" * 60)
        asyncio.run(register_monitors_via_api(all_monitors))


if __name__ == "__main__":
    main()
