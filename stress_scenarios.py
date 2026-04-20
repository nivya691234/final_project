"""
stress_scenarios.py
-------------------
Helper script that drives the three aging scenarios described in
our paper so the analyzer can be demoed automatically.

Run this script before starting the monitor (or run it on the same
machine) and the processes will slowly degrade in memory, CPU and
thread count.  The defaults are shortened for an interactive demo
(roughly one minute for each phase) but you can tune rates and
start delays via command‑line flags.

Usage examples:
    # run all three generators in parallel
    python stress_scenarios.py --all

    # just exercise the memory leak
    python stress_scenarios.py --memory

    # cpu runaway begins after 30 seconds
    python stress_scenarios.py --cpu --cpu-delay 30

    # thread leak with a new thread every 2 seconds
    python stress_scenarios.py --threads --thread-interval 2

"""

import argparse
import logging
import math
import threading
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")


def memory_leak(rate_mb_per_sec: float = 5.0, duration: float | None = None) -> None:
    """Continuously append to a list to simulate a memory leak.

    ``rate_mb_per_sec`` controls how quickly memory grows.  ``duration``
    can be specified to stop after a certain number of seconds; ``None``
    means run forever (or until the user hits Ctrl+C).
    """

    hog: list[bytearray] = []
    chunk = int(1024 * 1024)  # allocate in 1‑MB chunks
    start = time.time()
    logging.info("memory_leak: starting, rate=%.1fMB/s", rate_mb_per_sec)

    try:
        while duration is None or time.time() - start < duration:
            # allocate enough chunks to approximate the desired rate
            to_alloc = int(rate_mb_per_sec)
            for _ in range(to_alloc):
                hog.append(bytearray(chunk))
            elapsed = time.time() - start
            logging.info("memory_leak: consumed %d MB (elapsed %.1fs)",
                         len(hog), elapsed)
            time.sleep(1.0)
    except MemoryError:
        logging.error("memory_leak: process ran out of memory")
    except KeyboardInterrupt:
        logging.info("memory_leak: interrupted by user")


def cpu_runaway(start_delay: float = 10.0, burn_percent: float = 50.0) -> None:
    """Start a busy‑loop after ``start_delay`` seconds.

    The ``burn_percent`` parameter is only a rough suggestion; the
    generator simply spins as fast as it can and the operating system
    will determine the actual CPU percentage.
    """

    logging.info("cpu_runaway: waiting %.1f seconds before spinning", start_delay)
    time.sleep(start_delay)
    logging.info("cpu_runaway: spinning (approx %.1g%% cpu)", burn_percent)

    try:
        while True:
            # perform some meaningless work; the loop itself is what burns
            x = 0
            for i in range(1000000):
                x += math.sqrt(i)
    except KeyboardInterrupt:
        logging.info("cpu_runaway: interrupted by user")


def thread_leak(start_delay: float = 20.0, spawn_interval: float = 5.0) -> None:
    """Periodically spawn a daemon thread that never terminates.

    A growing thread count is a common software aging symptom.  Threads
    are created after ``start_delay`` seconds and then every
    ``spawn_interval`` seconds thereafter.
    """

    def worker() -> None:
        # keep the thread alive doing nothing useful
        while True:
            time.sleep(1.0)

    logging.info("thread_leak: starting in %.1f seconds", start_delay)
    time.sleep(start_delay)

    threads: list[threading.Thread] = []
    try:
        while True:
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            threads.append(t)
            logging.info("thread_leak: spawned thread #%d", len(threads))
            time.sleep(spawn_interval)
    except KeyboardInterrupt:
        logging.info("thread_leak: interrupted by user (created %d threads)", len(threads))


def main() -> None:
    parser = argparse.ArgumentParser(description="Automated stress scenarios")
    parser.add_argument("--memory", action="store_true", help="run memory leak")
    parser.add_argument("--cpu", action="store_true", help="run cpu runaway")
    parser.add_argument("--threads", action="store_true", help="run thread leak")
    parser.add_argument("--all", action="store_true", help="run all scenarios")

    # parameters for tweaking behaviour
    parser.add_argument("--mem-rate", type=float, default=5.0,
                        help="memory leak rate in MB/sec")
    parser.add_argument("--cpu-delay", type=float, default=10.0,
                        help="seconds to wait before starting cpu burn")
    parser.add_argument("--cpu-burn", type=float, default=50.0,
                        help="approximate cpu %% to burn when spinning")
    parser.add_argument("--thread-delay", type=float, default=20.0,
                        help="seconds to wait before starting thread leaks")
    parser.add_argument("--thread-interval", type=float, default=5.0,
                        help="seconds between spawning new leaked threads")
    args = parser.parse_args()

    # decide which generators to run
    make = []
    if args.all or args.memory:
        make.append(threading.Thread(target=memory_leak,
                                      args=(args.mem_rate,), daemon=True))
    if args.all or args.cpu:
        make.append(threading.Thread(target=cpu_runaway,
                                      args=(args.cpu_delay, args.cpu_burn), daemon=True))
    if args.all or args.threads:
        make.append(threading.Thread(target=thread_leak,
                                      args=(args.thread_delay, args.thread_interval), daemon=True))

    if not make:
        parser.error("please specify at least one scenario or use --all")

    for t in make:
        t.start()

    # keep the main thread alive while others run
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logging.info("main: stopping all scenarios")


if __name__ == "__main__":
    main()
