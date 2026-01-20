import asyncio
import ipaddress
import os
from contextlib import suppress
from tqdm import tqdm

# ================== CONFIG ==================
PORTS = [8080, 3128, 8000, 8888, 8118, 443, 1080, 1081, 1085]
TIMEOUT = 2
CONCURRENCY = 400

RANGE_FILE = "range.txt"
OUTPUT_FILE = "output.txt"
ERROR_FILE = "errors.txt"

# Disable tqdm automatically in CI (GitHub Actions)
DISABLE_TQDM = os.getenv("CI", "false").lower() == "true"
# ============================================


class Stats:
    __slots__ = ("success", "fail")

    def __init__(self):
        self.success = 0
        self.fail = 0


async def scan_port(ip: str, port: int, sem: asyncio.Semaphore, stats: Stats, pbar):
    async with sem:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=TIMEOUT
            )

            writer.close()
            with suppress(Exception):
                await writer.wait_closed()

            async with aio_lock:
                with open(OUTPUT_FILE, "a") as f:
                    f.write(f"{ip}:{port}\n")
                stats.success += 1

        except Exception as e:
            async with aio_lock:
                with open(ERROR_FILE, "a") as f:
                    f.write(f"{ip}:{port} -> {type(e).__name__}\n")
                stats.fail += 1

        finally:
            if pbar:
                pbar.update(1)


def load_targets():
    networks = []

    with open(RANGE_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            networks.append(ipaddress.ip_network(line, strict=False))

    for net in networks:
        for ip in net.hosts():
            for port in PORTS:
                yield str(ip), port


async def main():
    # Always create files (even if empty)
    open(OUTPUT_FILE, "w").close()
    open(ERROR_FILE, "w").close()

    targets = list(load_targets())
    total = len(targets)

    sem = asyncio.Semaphore(CONCURRENCY)
    stats = Stats()

    pbar = tqdm(
        total=total,
        desc="Scanning",
        unit="conn",
        ncols=100,
        disable=DISABLE_TQDM
    )

    tasks = [
        asyncio.create_task(scan_port(ip, port, sem, stats, pbar))
        for ip, port in targets
    ]

    await asyncio.gather(*tasks)

    pbar.close()

    print("\nScan finished")
    print(f"Success : {stats.success}")
    print(f"Failed  : {stats.fail}")
    print(f"Output  : {OUTPUT_FILE}")
    print(f"Errors  : {ERROR_FILE}")


if __name__ == "__main__":
    aio_lock = asyncio.Lock()
    asyncio.run(main())
