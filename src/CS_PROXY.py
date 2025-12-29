import requests
from urllib.parse import urlparse
import os

TIMEOUT_SECONDS = 15

# === 关键：全局 Session，不读取任何系统代理 ===
session = requests.Session()
session.trust_env = False   # ⭐⭐⭐ 这行是救命的

def load_bytes(path_or_url: str) -> bytes:
    """
    支持：
    - 本地路径
    - https/http URL
    且：不走系统代理（避免 ProxyError / SSL EOF）
    """
    # 本地文件
    if os.path.exists(path_or_url):
        with open(path_or_url, "rb") as f:
            return f.read()

    # URL
    parsed = urlparse(path_or_url)
    if parsed.scheme in ("http", "https"):
        resp = session.get(path_or_url, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp.content

    raise ValueError(f"Unsupported path or url: {path_or_url}")


def to_inline_part(path_or_url: str, name: str):
    """
    示例占位函数，你原来这里是构造 multi-part / inline image
    """
    data = load_bytes(path_or_url)
    print(f"[OK] Loaded {name}, bytes = {len(data)}")
    return {
        "name": name,
        "bytes_len": len(data)
    }


# ================== 你的原始 URL ==================

PATTERN1 = "https://gin-clothes.oss-cn-hangzhou.aliyuncs.com/%E8%BE%93%E5%85%A5%E5%9B%BE%E5%83%8F/%E7%BA%B8%E5%B7%BE%E5%B1%95%E5%BC%80.png"
PATTERN2 = "https://gin-clothes.oss-cn-hangzhou.aliyuncs.com/%E8%BE%93%E5%85%A5%E5%9B%BE%E5%83%8F/%E6%B2%BF%E6%B5%B7%E5%A5%B3%E7%89%9B%E4%BB%947%E5%AF%B8.png"
PATTERN3 = "https://gin-clothes.oss-cn-hangzhou.aliyuncs.com/%E8%BE%93%E5%85%A5%E5%9B%BE%E5%83%8F/4.png"
MOCKUP   = "https://gin-clothes.oss-cn-hangzhou.aliyuncs.com/%E8%BE%93%E5%85%A5%E5%9B%BE%E5%83%8F/81X46RPHviL._AC_SX679_.jpg"


def main():
    part_A = to_inline_part(PATTERN1, "Image A")
    part_B = to_inline_part(PATTERN2, "Image B")
    part_C = to_inline_part(PATTERN3, "Image C")
    part_D = to_inline_part(MOCKUP,   "Mockup")

    print("\nAll images loaded successfully ✅")
    print(part_A, part_B, part_C, part_D)


if __name__ == "__main__":
    main()
