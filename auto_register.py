"""
Docker 컨테이너 및 호스트 프로세스 자동 감지 및 Uptime Kuma 모니터 등록 스크립트

사용법:
    python auto_register.py              # Docker 컨테이너 스캔 및 등록
    python auto_register.py --dry-run    # 등록하지 않고 미리보기만
    python auto_register.py --list       # 현재 등록된 모니터 목록
    python auto_register.py --include-host  # 호스트 프로세스도 포함
    python auto_register.py --host-only     # 호스트 프로세스만
    python auto_register.py --label <라벨>  # 라벨로 컨테이너 필터링
"""

import subprocess
import json
import asyncio
import argparse
import re
import shutil
from dataclasses import dataclass
from typing import Optional
import os
from dotenv import load_dotenv


def find_docker_executable() -> str:
    """Docker 실행 파일 경로 찾기"""
    # 1. PATH에서 찾기
    docker_path = shutil.which("docker")
    if docker_path:
        return docker_path

    # 2. Windows 기본 설치 경로들
    common_paths = [
        r"C:\Program Files\Docker\Docker\resources\bin\docker.exe",
        r"C:\ProgramData\DockerDesktop\version-bin\docker.exe",
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Docker\wsl\docker.exe"),
    ]

    for path in common_paths:
        if os.path.exists(path):
            return path

    # 3. 못 찾으면 기본값 (PATH에 의존)
    return "docker"

# .env 파일 로드
load_dotenv()

# Uptime Kuma 설정
KUMA_URL = os.getenv("KUMA_URL", "http://localhost:3001")
KUMA_USERNAME = os.getenv("KUMA_USERNAME", "")
KUMA_PASSWORD = os.getenv("KUMA_PASSWORD", "")

# Docker 호스트 설정 (원격 모니터링용)
DOCKER_HOST_IP = os.getenv("DOCKER_HOST_IP", "localhost")

# 컨테이너 필터링 설정
FILTER_LABEL = os.getenv("FILTER_LABEL", "")


@dataclass
class ContainerInfo:
    """Docker 컨테이너 정보"""
    name: str
    image: str
    ports: list[dict]
    status: str
    health: Optional[str] = None


@dataclass
class ProcessInfo:
    """호스트 프로세스 정보"""
    name: str
    pid: int
    port: int
    cmdline: list[str]
    status: str = "running"


def get_host_processes(exclude_ports: list[int] = None) -> list[ProcessInfo]:
    """호스트에서 실행 중인 리스닝 프로세스 목록 조회

    Args:
        exclude_ports: 제외할 포트 목록 (기본: 시스템 포트)
    """
    try:
        import psutil
    except ImportError:
        print("[WARN] psutil library required for host process detection.")
        print("   Install: pip install psutil")
        return []

    # 기본 제외 포트 (시스템 서비스)
    if exclude_ports is None:
        exclude_ports = [22, 135, 139, 445, 3389, 5040, 7680]

    processes = []
    seen_ports = set()

    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.status != 'LISTEN':
                continue

            port = conn.laddr.port

            # 제외 포트 및 중복 체크
            if port in exclude_ports or port in seen_ports:
                continue

            # 1024 이하 시스템 포트 제외 (선택적)
            if port < 1024:
                continue

            seen_ports.add(port)

            try:
                proc = psutil.Process(conn.pid)
                cmdline = proc.cmdline()

                # 프로세스 이름 결정
                name = proc.name()
                if 'python' in name.lower() and len(cmdline) > 1:
                    # Python 스크립트인 경우 스크립트 이름 사용
                    script = os.path.basename(cmdline[1]) if len(cmdline) > 1 else name
                    name = f"python:{script}"

                processes.append(ProcessInfo(
                    name=name,
                    pid=conn.pid,
                    port=port,
                    cmdline=cmdline,
                    status="running"
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    except psutil.AccessDenied:
        print("[WARN] Access denied. Run as administrator for full process list.")

    return processes


def get_docker_containers(label_filter: str = None) -> list[ContainerInfo]:
    """실행 중인 Docker 컨테이너 목록 조회

    Args:
        label_filter: 라벨 필터 (예: "monitor.project=side_monitor")
    """
    try:
        docker_cmd = find_docker_executable()
        cmd = [docker_cmd, "ps", "--format", "{{json .}}"]

        # 라벨 필터 적용
        filter_label = label_filter or FILTER_LABEL
        if filter_label:
            cmd.extend(["--filter", f"label={filter_label}"])

        result = subprocess.run(
            cmd,
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
        if e.stderr:
            print(f"  Detail: {e.stderr.strip()}")
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


def generate_monitor_config_for_process(process: ProcessInfo, host: str = None) -> dict:
    """프로세스 정보로 모니터 설정 생성

    Args:
        process: 호스트 프로세스 정보
        host: 모니터링 대상 호스트
    """
    target_host = host or DOCKER_HOST_IP

    # TCP 전용 포트 (데이터베이스, 캐시 등)
    tcp_only_ports = [5432, 3306, 27017, 6379, 5379, 11211, 9042]

    # HTTP 서비스로 추정되는 포트
    http_ports = [80, 443, 3000, 3001, 4000, 5000, 5001, 8000, 8080, 8096, 8443, 9000, 8920]

    port = process.port

    if port in tcp_only_ports:
        return {
            "type": "port",
            "name": f"[Host] {process.name}:{port} (TCP)",
            "hostname": target_host,
            "port": port,
            "interval": 60,
            "retryInterval": 60,
            "maxretries": 3,
        }
    elif port in http_ports or port >= 3000:
        monitor = {
            "type": "http",
            "name": f"[Host] {process.name}:{port}",
            "url": f"http://{target_host}:{port}",
            "method": "GET",
            "interval": 60,
            "retryInterval": 60,
            "maxretries": 3,
            "accepted_statuscodes": ["200-299", "300-399"],
        }

        # API/백엔드 프로세스는 /health 엔드포인트 시도
        if "api" in process.name.lower() or "backend" in process.name.lower():
            monitor["url"] = f"http://{target_host}:{port}/health"

        return monitor
    else:
        return {
            "type": "port",
            "name": f"[Host] {process.name}:{port} (TCP)",
            "hostname": target_host,
            "port": port,
            "interval": 60,
            "retryInterval": 60,
            "maxretries": 3,
        }


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


def print_process_summary(processes: list[ProcessInfo]):
    """호스트 프로세스 요약 출력"""
    print("\n" + "=" * 60)
    print("Running Host Processes")
    print("=" * 60)

    for p in processes:
        print(f"\n[HOST] {p.name}")
        print(f"   PID: {p.pid}")
        print(f"   Port: {p.port}")
        if p.cmdline:
            cmd_str = " ".join(p.cmdline[:3])
            if len(p.cmdline) > 3:
                cmd_str += " ..."
            print(f"   Cmd: {cmd_str}")


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
    parser = argparse.ArgumentParser(description="Docker 컨테이너 및 호스트 프로세스 자동 Uptime Kuma 등록")
    parser.add_argument("--dry-run", action="store_true", help="등록하지 않고 미리보기만")
    parser.add_argument("--list", action="store_true", help="현재 등록된 모니터 목록")
    parser.add_argument("--host", type=str, default=None,
                        help="Docker 호스트 IP/hostname (기본: DOCKER_HOST_IP 환경변수 또는 localhost)")
    parser.add_argument("--include-host", action="store_true",
                        help="호스트 프로세스도 포함")
    parser.add_argument("--host-only", action="store_true",
                        help="호스트 프로세스만 (Docker 제외)")
    parser.add_argument("--label", type=str, default=None,
                        help="라벨로 컨테이너 필터링 (예: monitor.project=myapp)")
    args = parser.parse_args()

    if args.list:
        asyncio.run(list_existing_monitors())
        return

    # 대상 호스트 결정
    target_host = args.host or DOCKER_HOST_IP

    all_monitors = []
    containers = []
    processes = []

    # Docker 컨테이너 조회 (--host-only가 아닌 경우)
    if not args.host_only:
        containers = get_docker_containers(label_filter=args.label)
        if containers:
            print_container_summary(containers)
            for c in containers:
                monitors = generate_monitor_config(c, host=target_host)
                all_monitors.extend(monitors)

    # 호스트 프로세스 조회 (--include-host 또는 --host-only인 경우)
    if args.include_host or args.host_only:
        # Docker 컨테이너가 사용 중인 포트 제외
        docker_ports = []
        for c in containers:
            for p in c.ports:
                docker_ports.append(p["host_port"])

        processes = get_host_processes(exclude_ports=docker_ports + [22, 135, 139, 445, 3389, 5040, 7680])
        if processes:
            print_process_summary(processes)
            for p in processes:
                monitor = generate_monitor_config_for_process(p, host=target_host)
                all_monitors.append(monitor)

    if not containers and not processes:
        print("No running Docker containers or host processes found.")
        return

    print(f"\nTarget host: {target_host}")

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
