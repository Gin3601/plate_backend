import os
import re
import json
import time
import random
from pathlib import Path
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# ================== 配置区 ==================
API_TOKEN = "sk-FiUqbvGqOOF0LlD1wGplLPRGfgtbowaRIvLfPgZls5Lm7t90"  # 用你自己的（建议用重置后的）
BASE_URL = "https://api.302.ai"

EDIT_ENDPOINT = f"{BASE_URL}/ws/api/v3/google/nano-banana-pro/edit"

# 输出设置
OUT_DIR = Path(".")  # 输出目录（可改）
OUT_PREFIX = "output_amazon_1x1"
OUT_EXT = "png"      # 你要 png 就 png；接口会返回 jpeg/png url，这里统一按 ext 存名
MAX_POLL_SECONDS = 300
POLL_INTERVAL = 2

# 网络设置
CONNECT_TIMEOUT = 15
READ_TIMEOUT = 180
TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)
RETRIES = 4

# 你的四张图
PATTERN1 = "https://gin-clothes.oss-cn-hangzhou.aliyuncs.com/%E8%BE%93%E5%85%A5%E5%9B%BE%E5%83%8F/%E7%BA%B8%E5%B7%BE%E5%B1%95%E5%BC%80.png"
PATTERN2 = "https://gin-clothes.oss-cn-hangzhou.aliyuncs.com/%E8%BE%93%E5%85%A5%E5%9B%BE%E5%83%8F/%E6%B2%BF%E6%B5%B7%E5%A5%B3%E7%89%9B%E4%BB%947%E5%AF%B8.png"
PATTERN3 = "https://gin-clothes.oss-cn-hangzhou.aliyuncs.com/%E8%BE%93%E5%85%A5%E5%9B%BE%E5%83%8F/4.png"
MOCKUP   = "https://gin-clothes.oss-cn-hangzhou.aliyuncs.com/%E8%BE%93%E5%85%A5%E5%9B%BE%E5%83%8F/81X46RPHviL._AC_SX679_.jpg"
# ===========================================

# 不读系统代理（关键）
session = requests.Session()
session.trust_env = False
NO_PROXY = {"http": None, "https": None}

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}


def request_with_retry(method: str, url: str, **kwargs) -> requests.Response:
    last_err = None
    for i in range(RETRIES):
        try:
            r = session.request(method, url, proxies=NO_PROXY, **kwargs)
            # 针对 429/5xx 重试
            if r.status_code in (429, 500, 502, 503, 504):
                raise RuntimeError(f"retryable http {r.status_code}: {r.text[:200]}")
            return r
        except Exception as e:
            last_err = e
            sleep = (2 ** i) + random.random()
            print(f"[retry {i+1}/{RETRIES}] {type(e).__name__}: {e} | sleep {sleep:.2f}s")
            time.sleep(sleep)
    raise RuntimeError(f"request failed after retries: {last_err}")


def poll_result(get_url: str, max_wait_s: int = MAX_POLL_SECONDS) -> dict:
    deadline = time.time() + max_wait_s
    while True:
        r = request_with_retry("GET", get_url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        j = r.json()
        data = j.get("data") or {}
        status = (data.get("status") or "").lower()

        if status in ("completed", "succeeded", "success"):
            return j
        if status in ("failed", "error"):
            raise RuntimeError(f"Task failed: {json.dumps(j, ensure_ascii=False)[:2000]}")

        if time.time() > deadline:
            raise TimeoutError(f"Polling timeout. Last: {json.dumps(j, ensure_ascii=False)[:500]}")

        time.sleep(POLL_INTERVAL)


def ensure_image_bytes(b: bytes) -> None:
    # PNG/JPG/WebP 头判断，防止保存成 HTML/JSON
    if b.startswith(b"\x89PNG\r\n\x1a\n"):
        return
    if b.startswith(b"\xff\xd8\xff"):
        return
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return
    sample = b[:200].decode("utf-8", errors="ignore")
    raise RuntimeError(f"Downloaded content is not an image. First 200 chars:\n{sample}")


def next_run_index(out_dir: Path, prefix: str) -> int:
    """
    扫描已有文件，自动生成下一次运行编号：
    output_amazon_1x1_0001.png, _0002.png ...
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d{{4}})\.")
    max_idx = 0
    for p in out_dir.iterdir():
        if not p.is_file():
            continue
        m = pattern.match(p.name)
        if m:
            max_idx = max(max_idx, int(m.group(1)))
    return max_idx + 1


def download_one(url: str) -> bytes:
    r = request_with_retry("GET", url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.content


def save_outputs_parallel(urls: List[str], out_dir: Path, prefix: str, ext: str) -> List[Path]:
    """
    并行下载 outputs，并保存：
    - 同一次 run：output_xxxx_0007_01.png, _02.png ...
    """
    run_idx = next_run_index(out_dir, prefix)
    saved_paths: List[Path] = []

    # 并行下载
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(urls)))) as ex:
        fut_map = {ex.submit(download_one, u): (i, u) for i, u in enumerate(urls, start=1)}
        for fut in as_completed(fut_map):
            i, u = fut_map[fut]
            data = fut.result()
            ensure_image_bytes(data)

            filename = f"{prefix}_{run_idx:04d}_{i:02d}.{ext}"
            path = out_dir / filename
            path.write_bytes(data)
            saved_paths.append(path)
            print(f"[saved] {path}  <-  {u}")

    # 按序返回
    saved_paths.sort()
    return saved_paths


def main():
    # 你的提示词（把你原来的完整提示词粘进来）
    prompt = """
你将收到 4 张图片：
- images[0]: 示例编辑图（四件套电商图，白底，包含：左上纸巾、右上叉子、左下6寸盘、右下9寸盘）——这是必须被编辑输出的基底图(canvas)
- images[1]: 花纹图1（必须原样保持，不可重绘/风格化/重新解释）
- images[2]: 花纹图2（必须原样保持，不可重绘/风格化/重新解释）
- images[3]: 花纹图3（必须原样保持，不可重绘/风格化/重新解释）

任务：精确贴图替换（exact texture replacement），不是重新设计。
在保持 images[0] 的布局、物体位置、比例、光影、清晰度、背景完全不变的情况下，只做表面印刷图案替换：

1) 将 images[1] 的花纹【原样】贴到 images[0] 左上角物体“纸巾”表面。
2) 将 images[2] 的花纹【原样】贴到 images[0] 左下角物体“6寸餐盘”表面。
3) 将 images[3] 的花纹【原样】贴到 images[0] 右下角物体“9寸餐盘”表面。

严格规则（必须遵守）：
- 花纹必须与输入完全一致：颜色、元素、文字、排版都不能变
- 不得重绘、不得风格化、不得“参考后重做”、不得生成相似图案
- 不裁剪、不拉伸、不旋转、不改比例；保持花纹原始布局
- 只替换物体表面纹理：不能改变物体形状、位置、数量、阴影、反光、边缘
- 背景保持纯白，输出亚马逊风格 1:1 电商产品图

输出：一张与 images[0] 同构图的白底1:1产品图，完成三处贴图替换。
""".strip()

    payload = {
        "prompt": prompt,
        # ⭐ 关键：模板放第一张 = 基底图
        "images": [MOCKUP, PATTERN1, PATTERN2, PATTERN3],
        "aspect_ratio": "1:1",
        "resolution": "1k",
        # 同步优先；如果网关仍返回未完成，也有轮询兜底
        "enable_sync_mode": True,
        "enable_base64_output": False,
    }

    t0 = time.time()
    r = request_with_retry(
        "POST",
        EDIT_ENDPOINT,
        headers=HEADERS,
        data=json.dumps(payload),
        timeout=TIMEOUT,
    )
    print("[api] HTTP:", r.status_code)
    if r.status_code != 200:
        print(r.text)
        raise RuntimeError("edit request failed")

    j = r.json()
    data = j.get("data") or {}
    status = (data.get("status") or "").lower()
    outputs = data.get("outputs") or []

    print("[api] message:", j.get("message"), "code:", j.get("code"), "status:", status)

    # 如果没 outputs，就轮询 urls.get
    if not outputs:
        get_url = (data.get("urls") or {}).get("get")
        if not get_url:
            raise RuntimeError(f"No outputs and no polling url: {json.dumps(j, ensure_ascii=False)[:2000]}")
        j2 = poll_result(get_url)
        data2 = j2.get("data") or {}
        outputs = data2.get("outputs") or []
        status2 = (data2.get("status") or "").lower()
        print("[poll] status:", status2)

    if not outputs:
        raise RuntimeError(f"No outputs in final response: {json.dumps(j, ensure_ascii=False)[:2000]}")

    # 并行下载并保存（每次 run 自动编号 + 多输出自动 _01/_02）
    saved = save_outputs_parallel(outputs, OUT_DIR, OUT_PREFIX, OUT_EXT)

    print(f"[done] saved {len(saved)} file(s)")
    print(f"[done] elapsed: {time.time() - t0:.2f}s")


if __name__ == "__main__":
    main()
