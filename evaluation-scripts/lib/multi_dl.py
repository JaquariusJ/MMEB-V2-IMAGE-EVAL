#!/usr/bin/env python3
"""Multi-connection downloader (HTTP range requests) to beat per-connection throttling.

Usage:
  python multi_dl.py <url> <dest> [conns=16]

Used for the MMEB-V2 image-tasks tar.gz (~6.7GB), where snapshot_download is slow.
Resumable-safe only on full re-run (re-downloads from scratch if .part is partial);
verify with `gzip -t <dest>` if interrupted.
"""
import sys
import os
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor

url = sys.argv[1]
dest = sys.argv[2]
conns = int(sys.argv[3]) if len(sys.argv) > 3 else 16

sess = requests.Session()
h = sess.head(url, timeout=30, allow_redirects=True)
size = int(h.headers.get("Content-Length", 0))
ar = h.headers.get("Accept-Ranges", "").lower() == "bytes"
print(f"size={size} accept_ranges={ar} conns={conns}", flush=True)

os.makedirs(os.path.dirname(dest), exist_ok=True)
if size and os.path.exists(dest) and os.path.getsize(dest) == size:
    print("already complete", flush=True)
    sys.exit(0)

tmp = dest + ".part"
errors = []

if ar and size:
    chunk = (size + conns - 1) // conns
    with open(tmp, "wb") as f:
        f.truncate(size)
    done = [0] * conns
    lock = threading.Lock()

    def dl(i):
        start = i * chunk
        end = min(start + chunk - 1, size - 1)
        if start > end:
            return
        for attempt in range(6):
            try:
                r = sess.get(url, headers={"Range": f"bytes={start}-{end}"}, stream=True, timeout=120)
                with open(tmp, "r+b") as f:
                    f.seek(start)
                    for c in r.iter_content(256 * 1024):
                        f.write(c)
                        with lock:
                            done[i] += len(c)
                return
            except Exception as e:
                if attempt == 5:
                    errors.append(f"chunk{i}: {e}")
                time.sleep(2)

    stop = [False]

    def report():
        while not stop[0]:
            time.sleep(15)
            tot = sum(done)
            pct = 100 * tot / size if size else 0
            print(f"  {tot // 1024 // 1024}MB / {size // 1024 // 1024}MB ({pct:.1f}%)", flush=True)

    t = threading.Thread(target=report, daemon=True)
    t.start()
    with ThreadPoolExecutor(max_workers=conns) as ex:
        list(ex.map(dl, range(conns)))
    stop[0] = True
    if errors:
        print("ERRORS:", errors, flush=True)
        sys.exit(1)
    os.rename(tmp, dest)
    print("DONE", flush=True)
else:
    r = sess.get(url, stream=True, timeout=120)
    with open(tmp, "wb") as f:
        for c in r.iter_content(256 * 1024):
            f.write(c)
    os.rename(tmp, dest)
    print("DONE single", flush=True)
