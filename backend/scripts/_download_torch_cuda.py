"""从阿里云 pytorch 镜像 CDN 续传下载 CUDA 版 torch wheel（一次性工具）。

镜像 simple 索引未收录 cu128 cp314 win 版本，但 CDN 文件可直接下载：
torch 2.9.1+cu128 (cp314, win_amd64) —— 满足 tabicl torch>=2.2 要求，
cu128 运行时与 12.7 驱动（minor version compatibility）兼容 RTX 4060。
"""

import sys
import time
from pathlib import Path

import requests

URL = (
    "https://mirrors.aliyun.com/pytorch-wheels/cu128/"
    "torch-2.9.1%2Bcu128-cp314-cp314-win_amd64.whl"
)
OUT = Path(__file__).resolve().parent.parent / ".downloads" / "torch-2.9.1+cu128-cp314-cp314-win_amd64.whl"
CHUNK = 1 << 20


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.trust_env = False
    for attempt in range(1, 40):
        done = OUT.stat().st_size if OUT.exists() else 0
        try:
            headers = {"Range": f"bytes={done}-"} if done else {}
            with session.get(URL, headers=headers, timeout=(10, 60), stream=True) as r:
                total = int(r.headers.get("Content-Length", 0)) + done
                if r.status_code == 416:
                    print(f"[done] 文件已完整: {done} 字节")
                    return 0
                r.raise_for_status()
                t0 = time.time()
                n0 = done
                with OUT.open("ab" if done else "wb") as f:
                    for chunk in r.iter_content(CHUNK):
                        f.write(chunk)
                done = OUT.stat().st_size
                dt = max(1e-3, time.time() - t0)
                print(f"[尝试{attempt}] 本次 {(done - n0)/1024/1024:.1f}MB @ {(done-n0)/dt/1024/1024:.2f}MB/s, "
                      f"累计 {done/1024/1024:.0f}/{total/1024/1024:.0f} MB", flush=True)
                if total and done >= total:
                    print(f"[done] 下载完成: {OUT}")
                    return 0
        except Exception as exc:
            print(f"[尝试{attempt}] 中断({type(exc).__name__}), 已有 {done/1024/1024:.0f} MB, 续传...", flush=True)
            time.sleep(3)
    print("[fail] 多次续传未完成")
    return 1


if __name__ == "__main__":
    sys.exit(main())
