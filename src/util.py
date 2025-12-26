import base64
import re
import requests
import os
import time
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np
import os
# 1. 将本地图片转换为Base64编码
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
def extract_image_urls(text):
    """
    从文本中提取Markdown格式的图片URL，只返回第一个匹配的URL
    """
    if not text:
        return ""

    # 使用正则表达式匹配Markdown图片语法
    pattern = r'!\[.*?\]\((.*?)\)'
    urls = re.findall(pattern, text)

    # 返回第一个URL，如果没有找到则返回空字符串
    if urls:
        # 去除可能的空格和反引号
        return urls[0].strip().strip('`')
    else:
        return ""


def download_image(url, output_dir, filename=None):
    """
    下载图片并保存到指定目录
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 如果未指定文件名，从URL中提取或生成
    if not filename:
        # 尝试从URL中提取文件名
        filename = url.split('/')[-1]
        # 如果URL没有明确的文件名，生成一个时间戳文件名
        if not filename or '.' not in filename:

            filename = f"generated_image_{int(time.time())}.png"

    # 完整的输出路径
    output_path = os.path.join(output_dir, filename)

    try:
        # 下载图片
        response = requests.get(url, stream=True)
        response.raise_for_status()  # 检查是否下载成功

        # 保存图片
        with open(output_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)

        print(f"图片已保存到: {output_path}")
        return output_path
    except Exception as e:
        print(f"下载图片失败: {str(e)}")
        return None


def download_and_save_images(image_urls, output_dir="./template_images", filename_prefix="generated_plate"):
    """
    下载并保存多张图片到指定目录

    Args:
        image_urls: 图片URL列表
        output_dir: 输出目录路径，默认为"./template_images"
        filename_prefix: 文件名前缀，默认为"generated_plate"

    Returns:
        保存成功的图片路径列表
    """
    saved_paths = []

    if image_urls:
        print(f"找到 {len(image_urls)} 张图片，开始下载...")
        for i, url in enumerate(image_urls):
            # 为每张图片生成一个有意义的文件名
            # url_last_part = url.split('/')[-1]
            filename = f"{filename_prefix}_{int(time.time())}_{i + 1}.png"
            saved_path = download_image(url, output_dir, filename)
            if saved_path:
                saved_paths.append(saved_path)
        print(f"下载完成，成功保存 {len(saved_paths)} 张图片")
    else:
        print("未找到图片URL")

    return saved_paths




# ... 保留原有的导入和函数定义 ...

# 添加一个显示图片的辅助函数
def display_images_side_by_side(image_paths, titles=None):
    """
    在PyCharm中并排显示多张图片

    Args:
        image_paths: 图片路径列表
        titles: 图片标题列表，如果为None则使用默认标题
    """
    # 确保图片路径存在
    valid_paths = []
    valid_titles = []
    for i, path in enumerate(image_paths):
        if os.path.exists(path):
            valid_paths.append(path)
            if titles:
                valid_titles.append(titles[i])
            else:
                # 默认标题格式
                title_map = {
                    0: "input_ref_image1",
                    1: "input_ref_image2",
                    2: "user_image",
                    3: "output_ref_image1",
                    4: "output_ref_image2"
                }
                valid_titles.append(title_map.get(i, f"Image {i + 1}"))
        else:
            print(f"警告: 图片文件不存在: {path}")

    if not valid_paths:
        print("错误: 没有找到有效的图片文件")
        return

    # 创建子图布局
    num_images = len(valid_paths)
    fig, axes = plt.subplots(1, num_images, figsize=(5 * num_images, 5))

    # 如果只有一张图片，axes不会是数组
    if num_images == 1:
        axes = [axes]

    # 加载并显示每张图片
    for i, (path, ax) in enumerate(zip(valid_paths, axes)):
        try:
            # 使用PIL加载图片
            img = Image.open(path)
            # 转换为numpy数组以便matplotlib显示
            img_array = np.array(img)
            # 显示图片
            ax.imshow(img_array)
            ax.set_title(valid_titles[i])
            ax.axis('off')  # 不显示坐标轴
        except Exception as e:
            print(f"加载图片 {path} 时出错: {str(e)}")

    plt.tight_layout()  # 调整布局，避免标题重叠
    plt.show()  # 显示图片
