import json
import time
import re
from pathlib import Path
from typing import List, Optional

import requests


# ================== 配置区（只改这里） ==================
API_TOKEN = "sk-FiUqbvGqOOF0LlD1wGplLPRGfgtbowaRIvLfPgZls5Lm7t90"  # <- 改成你的 Key
BASE_URL = "https://api.302.ai"
EDIT_ENDPOINT = f"{BASE_URL}/ws/api/v3/google/nano-banana-pro/edit"

# 1) 模板图（示例四件套那张）
MOCKUP = "https://gin-clothes.oss-cn-hangzhou.aliyuncs.com/%E8%BE%93%E5%85%A5%E5%9B%BE%E5%83%8F/81X46RPHviL._AC_SX679_.jpg"

# 2) 三张花纹图：纸巾、小盘、大盘（按你自己的映射替换）
PATTERN_NAPKIN = "https://gin-clothes.oss-cn-hangzhou.aliyuncs.com/%E8%BE%93%E5%85%A5%E5%9B%BE%E5%83%8F/%E7%BA%B8%E5%B7%BE%E5%B1%95%E5%BC%80.png"
PATTERN_SMALL  = "https://gin-clothes.oss-cn-hangzhou.aliyuncs.com/%E8%BE%93%E5%85%A5%E5%9B%BE%E5%83%8F/%E6%B2%BF%E6%B5%B7%E5%A5%B3%E7%89%9B%E4%BB%947%E5%AF%B8.png"
PATTERN_LARGE  = "https://gin-clothes.oss-cn-hangzhou.aliyuncs.com/%E8%BE%93%E5%85%A5%E5%9B%BE%E5%83%8F/4.png"

# 输出
OUT_DIR = Path(".")
OUT_PREFIX = "sku"
OUT_EXT = "png"

# 生成参数
RESOLUTION = "2k"   # 1k/2k/4k
ASPECT_RATIO = "1:1"
# =======================================================


# 网络参数（不走系统代理）
TIMEOUT = (15, 240)
session = requests.Session()
session.trust_env = False
NO_PROXY = {"http": None, "https": None}

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}


PROMPT_REPLACE = """
You will receive 4 images:
- images[0]: base mockup photo (white background product set). Keep layout unchanged.
- images[1]: napkin pattern (use as-is).
- images[2]: small plate pattern (use as-is).
- images[3]: large plate pattern (use as-is).

Task: exact texture replacement ONLY (not redesign).
Keep images[0] composition, object positions, proportions, lighting, shadows, reflections, edges, and pure white background unchanged.

Replace printed surface texture:
1) Apply images[1] onto the napkins (top-left item).
2) Apply images[2] onto the small plate (bottom-left plate).
3) Apply images[3] onto the large plate (bottom-right plate).

Strict rules:
- Do NOT redraw/reinterpret patterns; keep patterns identical (colors, layout, text, elements).
- Do NOT add/remove objects; do NOT change object shapes/positions.
Output: photorealistic e-commerce white background product image.
""".strip()


PROMPT_INFOGRAPHIC = """
Create a clean e-commerce infographic (NOT a photo redesign).
Use images[0] as the ONLY product source. Do NOT redraw products. Do NOT change patterns.
Extract the products from images[0] and compose a new 1:1 infographic.

Header:
- White background
- Top black header bar
- Yellow badge on the left: "96 PIECES"
- Center title in white: "PACKAGE INCLUDES"
- Clean sans-serif font, crisp readable text

Layout (2x2 grid):
- Top-left: large dinner plate from images[0]
- Top-right: small dinner plate from images[0]
- Bottom-left: napkins from images[0]
- Bottom-right: forks from images[0]
All items aligned with consistent margins.

Measurements (exact text):
- Add thin black vertical measurement line on the LEFT of each item with end caps:
  - Top-left: "9inch"
  - Top-right: "7inch"
  - Bottom-left: "6.5inch"
  - Bottom-right: "7.3in"

Labels (exact text, black rounded pill with white text under each item):
- "24×Dinner Plate"
- "24×Dinner Plate"
- "24×Napkins"
- "24×Forks"

If you cannot follow exactly, return a plain white image with text "FAILED".
""".strip()


def next_run_id(out_dir: Path, prefix: str) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    pat = re.compile(rf"^{re.escape(prefix)}_(\d{{4}})_")
    m = 0
    for p in out_dir.iterdir():
        if p.is_file():
            mm = pat.match(p.name)
            if mm:
                m = max(m, int(mm.group(1)))
    return m + 1

def post_edit(payload: dict) -> dict:
    # 1) 本地先断言：payload 里一定有 prompt/images
    assert isinstance(payload, dict), type(payload)
    assert "prompt" in payload and isinstance(payload["prompt"], str) and payload["prompt"].strip(), \
        f'payload missing "prompt": keys={list(payload.keys())}'
    assert "images" in payload and isinstance(payload["images"], list) and len(payload["images"]) > 0, \
        f'payload missing "images": {payload.get("images")}'

    # 2) 打印将要发送的关键信息（你会看到 prompt 到底有没有）
    print("\n[DEBUG] sending payload keys:", list(payload.keys()))
    print("[DEBUG] prompt head:", payload["prompt"][:80].replace("\n", "\\n"))
    print("[DEBUG] images count:", len(payload["images"]))
    print("[DEBUG] endpoint:", EDIT_ENDPOINT)

    # 3) ✅ 最稳：不用你手写 Content-Type，让 requests 自己生成正确头
    headers = {"Authorization": f"Bearer {API_TOKEN}"}

    # 4) 发请求：必须 json=payload
    r = session.post(
        EDIT_ENDPOINT,
        headers=headers,
        json=payload,
        timeout=TIMEOUT,
        proxies=NO_PROXY,
    )

    # 5) 打印“实际发送出去的 body”（这一步最关键）
    try:
        sent_body = r.request.body
        if isinstance(sent_body, (bytes, bytearray)):
            sent_body_preview = sent_body[:300].decode("utf-8", errors="replace")
        else:
            sent_body_preview = str(sent_body)[:300]
        print("[DEBUG] request body preview:", sent_body_preview)
    except Exception as e:
        print("[DEBUG] cannot inspect request body:", repr(e))

    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:1200]}")
    return r.json()



def poll_result(get_url: str, max_wait_s: int = 300) -> dict:
    deadline = time.time() + max_wait_s
    while True:
        r = session.get(get_url, headers=HEADERS, timeout=TIMEOUT, proxies=NO_PROXY)
        r.raise_for_status()
        j = r.json()
        data = j.get("data") or {}
        status = (data.get("status") or "").lower()
        if status in ("completed", "succeeded", "success"):
            return j
        if status in ("failed", "error"):
            return j
        if time.time() > deadline:
            return j
        time.sleep(2)


def get_outputs(resp: dict) -> List[str]:
    data = resp.get("data") or {}
    outputs = data.get("outputs") or []
    if outputs:
        return outputs

    # 兜底：有时 outputs 为空但给了 urls.get
    get_url = (data.get("urls") or {}).get("get")
    if get_url:
        j2 = poll_result(get_url)
        data2 = j2.get("data") or {}
        return data2.get("outputs") or []
    return []


def download(url: str) -> bytes:
    r = session.get(url, timeout=TIMEOUT, proxies=NO_PROXY)
    r.raise_for_status()
    return r.content


def save_bytes(b: bytes, path: Path):
    path.write_bytes(b)
    print("[saved]", path)

print("\n=== QUICK TEST ===")
test_payload = {
    "prompt": "Return the same image without changes.",
    "images": [MOCKUP],
    "aspect_ratio": "1:1",
    "resolution": "1k",
    "enable_sync_mode": True,
    "enable_base64_output": False,
}
print(post_edit(test_payload))
print("=== QUICK TEST DONE ===\n")



def main():
    run_id = next_run_id(OUT_DIR, OUT_PREFIX)

    # ================= Step 1：贴花纹替换（hero） =================
    payload1 = {
        "prompt": PROMPT_REPLACE,
        "images": [MOCKUP, PATTERN_NAPKIN, PATTERN_SMALL, PATTERN_LARGE],
        "aspect_ratio": ASPECT_RATIO,
        "resolution": RESOLUTION,
        "enable_sync_mode": True,
        "enable_base64_output": False,
    }

    print("=== Step1: texture replacement → hero ===")
    resp1 = post_edit(payload1)
    outs1 = get_outputs(resp1)
    if not outs1:
        raise RuntimeError("Step1 no outputs:\n" + json.dumps(resp1, ensure_ascii=False)[:2000])

    hero_url = outs1[0]
    hero_path = OUT_DIR / f"{OUT_PREFIX}_{run_id:04d}_01_hero.{OUT_EXT}"
    save_bytes(download(hero_url), hero_path)
    print("[hero_url]", hero_url)

    # ================= Step 2：基于 hero 生成信息图 =================
    payload2 = {
        "prompt": PROMPT_INFOGRAPHIC,
        "images": [hero_url],
        "aspect_ratio": "1:1",
        "resolution": RESOLUTION,
        "enable_sync_mode": True,
        "enable_base64_output": False,
    }

    print("\n=== Step2: hero → infographic ===")
    resp2 = post_edit(payload2)
    outs2 = get_outputs(resp2)
    if not outs2:
        raise RuntimeError("Step2 no outputs:\n" + json.dumps(resp2, ensure_ascii=False)[:2000])

    info_url = outs2[0]
    info_path = OUT_DIR / f"{OUT_PREFIX}_{run_id:04d}_02_infographic.{OUT_EXT}"
    save_bytes(download(info_url), info_path)
    print("[info_url]", info_url)

    print("\nDONE.")
    print("Hero:", hero_path)
    print("Infographic:", info_path)


if __name__ == "__main__":
    main()
