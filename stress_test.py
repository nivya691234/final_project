"""
stress_test.py
--------------
A script designed to artificially age a software process.
It slowly consumes memory and CPU over time to trigger the
Software Aging Analyser's detection, prediction, and auto-remediation.
"""

import time
import math
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

def consume_resources():
    memory_hog = []
    chunk_size = 5 * 1024 * 1024  # 5 MB
    
    logging.info("Starting artificial aging process (stress_test.py)...")
    logging.info("PID: %d", __import__("os").getpid())
    
    start_time = time.time()
    
    try:
        while True:
            # 1. Leak Memory
            memory_hog.append(bytearray(chunk_size))
            
            # 2. Consume CPU (increasingly tighter loop)
            # The longer it runs, the more iterations it does per tick
            elapsed = time.time() - start_time
            iterations = int(500000 + (elapsed * 50000))
            
            for i in range(iterations):
                _ = math.sqrt(i) * math.sqrt(i)
                
            logging.info(f"Leaked {len(memory_hog) * 5} MB. Elapsed: {elapsed:.1f}s")
            
            # Sleep to allow psutil to sample it
            time.sleep(2.0)
            
    except MemoryError:
        logging.error("Out of memory!")
    except KeyboardInterrupt:
        logging.info("Stress test stopped by user.")

if __name__ == "__main__":
    consume_resources()
