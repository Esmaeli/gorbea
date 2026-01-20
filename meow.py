import asyncio
import ipaddress
from tqdm import tqdm

# ---------- تنظیمات ----------
PORTS = [80, 443]
TIMEOUT = 1
CONCURRENCY = 200
OUTPUT_FILE = "output.txt"
RANGE_FILE = "range.txt"
# ----------------------------


success_count = 0
fail_count = 0
counter_lock = asyncio.Lock()


async def scan_port(ip, port, semaphore, pbar):
    global success_count, fail_count

    async with semaphore:
        try:
            conn = asyncio.open_connection(ip, port)
            reader, writer = await asyncio.wait_for(conn, timeout=TIMEOUT)
            writer.close()
            await writer.wait_closed()

            result = f"{ip}:{port}"
            print(result)

            with open(OUTPUT_FILE, "a") as f:
                f.write(result + "\n")

            async with counter_lock:
                success_count += 1

        except:
            async with counter_lock:
                fail_count += 1

        finally:
            pbar.update(1)
            pbar.set_postfix(
                success=success_count,
                fail=fail_count
            )


async def main():
    semaphore = asyncio.Semaphore(CONCURRENCY)

    total = 0
    networks = []

    with open(RANGE_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            net = ipaddress.ip_network(line, strict=False)
            networks.append(net)
            total += net.num_addresses * len(PORTS)

    pbar = tqdm(
        total=total,
        desc="Scanning",
        unit="scan",
        ncols=110
    )

    tasks = []

    for network in networks:
        for ip in network.hosts():
            for port in PORTS:
                tasks.append(
                    asyncio.create_task(
                        scan_port(str(ip), port, semaphore, pbar)
                    )
                )

                if len(tasks) >= CONCURRENCY * 2:
                    await asyncio.gather(*tasks)
                    tasks.clear()

    if tasks:
        await asyncio.gather(*tasks)

    pbar.close()

    print("\nScan finished!")
    print(f"Success : {success_count}")
    print(f"Failed  : {fail_count}")


if __name__ == "__main__":
    asyncio.run(main())
