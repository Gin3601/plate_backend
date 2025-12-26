import os

# 强制移除代理设置，确保直连 302.ai
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("all_proxy", None)
from dotenv import load_dotenv


# 加载.env文件中的环境变量
load_dotenv()

# 从环境变量中获取配置
BASE_URL = os.getenv("BASE_URL", "https://api.302.ai/v1")  # 提供默认值作为备用
API_KEY = os.getenv("API_KEY", "")

from langchain_openai import ChatOpenAI

# 初始化模型
gemini_flash_image_model = ChatOpenAI(
    model="gemini-2.5-flash-image",  # 请根据平台提供的模型名称修改
    base_url=BASE_URL,
    api_key=API_KEY
)
gemini_flash_image_model_3 = ChatOpenAI(
    model="gemini-3-pro-image-preview",  # 请根据平台提供的模型名称修改
    base_url=BASE_URL,
    api_key=API_KEY
)
qwen3_vl_plus_model = ChatOpenAI(
    model="qwen3-vl-plus-2025-09-23",  # 请根据平台提供的模型名称修改
    base_url=BASE_URL,
    api_key=API_KEY
)
qwen_vl_max_model = ChatOpenAI(
    model="qwen-vl-max-latest",  # 请根据平台提供的模型名称修改
    base_url=BASE_URL,
    api_key=API_KEY
)
qwen_max=ChatOpenAI(
    model="qwen3-max-preview",  # 请根据平台提供的模型名称修改
    base_url=BASE_URL,
    api_key=API_KEY
)
doubao_model = ChatOpenAI(
    model="doubao-seed-1-6-vision-250815",  # 请根据平台提供的模型名称修改
    base_url=BASE_URL,
    api_key=API_KEY
)
#不可用
qwen_image_edit = ChatOpenAI(
    model="qwen-image-edit",  # 请根据平台提供的模型名称修改
    base_url=BASE_URL,
    api_key=API_KEY
)
gpt_o3_pro= ChatOpenAI(
    model="o3-pro",  # 请根据平台提供的模型名称修改
    base_url=BASE_URL,
    api_key=API_KEY
)
gpt_image_model = ChatOpenAI(
    model="gpt-image-1",
    base_url=BASE_URL,
    api_key=API_KEY
)
