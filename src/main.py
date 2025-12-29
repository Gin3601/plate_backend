from fastapi import FastAPI, Form, APIRouter
from typing import Literal
from src.model_api import *
from src.util import encode_image, extract_image_urls
from langchain_core.messages import HumanMessage, SystemMessage
from fastapi import HTTPException, UploadFile, File
import concurrent.futures
import tempfile
import os
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from fastapi.middleware.cors import CORSMiddleware
router = APIRouter()
def load_default_images(image_type):
    """
    根据选择的图片类型加载默认参考图片路径
    """
    # 获取当前脚本文件所在目录的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 根据不同类型选择不同的默认图片路径，使用相对于当前脚本文件的路径
    input_paths = [
        os.path.join(current_dir, "template_images", "source", "1.jpg"),
        os.path.join(current_dir, "template_images", "source", "2.jpg"),
        os.path.join(current_dir, "template_images", "source", "3.jpg")
    ]
    if image_type == "商品图":
        output_paths = [
            os.path.join(current_dir, "template_images", "good_img", "1.jpg"),
            os.path.join(current_dir, "template_images", "good_img", "2.jpg"),
            os.path.join(current_dir, "template_images", "good_img", "3.jpg")
        ]
    elif image_type == "尺寸图":
        output_paths = [
            os.path.join(current_dir, "template_images", "size_img", "1.jpg"),
            os.path.join(current_dir, "template_images", "size_img", "2.jpg"),
            os.path.join(current_dir, "template_images", "size_img", "3.jpg")
        ]
    elif image_type == "商品展示图1":
        output_paths = [
            os.path.join(current_dir, "template_images", "four_img", "1.jpg"),
            os.path.join(current_dir, "template_images", "four_img", "2.jpg"),
            os.path.join(current_dir, "template_images", "four_img", "3.jpg")
        ]
    elif image_type == "商品展示图2":
        output_paths = [
            os.path.join(current_dir, "template_images", "intro_img", "1.jpg"),
            os.path.join(current_dir, "template_images", "intro_img", "2.jpg"),
            os.path.join(current_dir, "template_images", "intro_img", "3.jpg")
        ]
    elif image_type == "场景图1":
        output_paths = [
            os.path.join(current_dir, "template_images", "no_people_img", "1.jpg"),
            os.path.join(current_dir, "template_images", "no_people_img", "2.jpg"),
            os.path.join(current_dir, "template_images", "no_people_img", "3.jpg")
        ]
    elif image_type == "场景图2":
        output_paths = [
            os.path.join(current_dir, "template_images", "people_img", "1.jpg"),
            os.path.join(current_dir, "template_images", "people_img", "2.jpg"),
            os.path.join(current_dir, "template_images", "people_img", "3.jpg")
        ]
    else:
        # 自定义输入或其他情况，返回None
        return None
    
    # 检查所有文件是否存在
    all_paths = []
    for i in range(3):
        if os.path.exists(input_paths[i]) and os.path.exists(output_paths[i]):
            all_paths.extend([input_paths[i], output_paths[i]])
        else:
            # 如果任何一个文件不存在，返回None
            return None
    
    return all_paths

def create_message_with_images(image_paths:list=[], prompt:str="", system_prompt=""):
    """
    创建包含图片和提示词的消息列表，支持系统提示词和用户提示词
    """
    messages = []

    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))

    user_content = [{"type": "text", "text": prompt}]
    if image_paths:
        for img_path in image_paths:
            mime_type = f"image/{img_path.split('.')[-1].lower()}"
            if mime_type == "image/jpg":
                mime_type = "image/jpeg"

            base64_image = encode_image(img_path)
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{base64_image}"
                }
            })

    messages.append(HumanMessage(content=user_content))
    return messages

def generate_prompt(image_paths, prompt):
    """生成编辑提示词"""
    messages = create_message_with_images(image_paths, prompt, system_prompt="""
    编辑指令生成器
    你是一名专业的编辑指令生成器。你的任务是根据用户提供的输入图片和输出图片，分析两者之间的抽象编辑逻辑和视觉转换关系，生成一个通用的、可迁移的编辑指令模板，然后针对待处理图片，根据模板生成具体的编辑指令。
    核心原则
    抽象化分析：重点分析输入→输出的转换逻辑，而非具体的图像内容
    可迁移性：生成的指令应适用于同类别的其他图片
    模式识别：识别视觉转换的通用模式
    转换逻辑分析维度
    1. 视觉属性转换
    色彩关系：色调、饱和度、明度的变化模式
    光影模式：光源方向、强度、阴影特性的变化
    纹理特征：表面质感、细节层次的变化
    2. 构图结构转换
    空间关系：物体位置、大小比例的变化规律
    视觉重心：视觉焦点和注意力分布的变化
    3. 风格特征转换
    艺术风格：笔触、色彩运用、构图手法的特征
    时代特征：时代风格元素的抽象特征
    抽象化描述规则
    使用相对参数而非绝对数值
    描述转换关系而非具体结果
    避免引用具体对象，关注视觉特征
    结果只返回输出详细可直接使用的针对待处理图片的中文提示词文本，不要返回其他任何内容
    """)

    response = qwen_vl_max_model.invoke(messages)
    return response.content


def add_user_description(prompt: str) -> str:
    """添加用户描述到提示词"""
    messages = create_message_with_images(prompt=prompt,system_prompt="""
     你是一个图像生成提示词修改助手，你的任务是根据用户输入的描述，对原始的图像生成提示词进行【必要且最小化】的增加或修改。

    【最高优先级规则（必须严格遵守）】
    - 你只能使用【原始提示词中已有的信息】和【用户描述中明确提到的信息】。
    - 严禁为了“丰富画面”而新增任何用户未提及的物体、道具、装饰、背景元素或示例内容。
    - 严禁添加与主体常见但用户未明确提及的关联物（例如：杯子 → 咖啡豆、杯垫；人物 → 饰品、包、手表等）。
    - 严禁使用“例如 / 比如 / 如 / 等 / such as / including”等方式扩展对象或元素列表。
    - 若原始提示词中包含示例性扩展内容（如“例如(…)”），在用户未明确要求时应删除该示例，仅保留抽象或概括性描述。

    【任务要求】
    1. 如果原始提示词中已包含用户描述的对象，但细节不同，必须仅根据用户描述修改对应细节。
    2. 如果原始提示词中未包含用户描述的对象，才允许将该对象添加进原始提示词中。
    3. 如果用户描述是关键词组合，只能将这些关键词用于修正或补充原始提示词中已有对象，不得引入新对象。
    4. 对于原始提示词中包含但用户描述中未提及的对象，必须保持原样，不删除、不扩写。
    5. 修改后的提示词应符合现实常识，避免出现逻辑或常理矛盾的描述（例如：“冬天但人物穿着短袖”）。
    6. 结果只返回【最终修改后的提示词文本】，不要返回任何解释、分析或其他内容。

    【修改示例】
    示例 1：
    原始提示词：“一张人物照片”
    用户描述：“人物是一个年轻人，穿着白色的衬衫”
    修改后的提示词：
    “一张人物照片，人物是一个年轻人，穿着白色的衬衫”

    示例 2：
    原始提示词：“一张青年人在散步照片”
    用户描述：“老年人，黑色的衬衫，公园”
    修改后的提示词：
    “一张人物在散步的照片，人物是一个老年人，穿着黑色的衬衫，背景是公园”

    示例 3：
    原始提示词：
    “一家人在餐桌前庆祝生日女儿，1个中年男性父亲，1个青年男性儿子，1个幼年女儿，一位中年女性母亲”
    用户描述：
    “圣诞节，圣诞树，冬天”
    修改后的提示词：
    “一家人在餐桌前庆祝圣诞节，1个中年男性父亲，1个青年男性儿子，1个幼年女儿，一位中年女性母亲，背景包含一颗圣诞树，窗外是冬天在下雪”

    下面我将给出原始提示词和用户描述：

    """)
    response=qwen_max.invoke(messages)

    return response.content

def polish_prompt(image_paths, prompt):
    messages = create_message_with_images(image_paths, prompt, system_prompt="""
用户需要进行根据参考示例图，将待处理图片转换为类似示例图的任务，图二是图一的转换后图片， 图四是图三的转换后图片，图六是图五的转换后图片，图七是待处理图片。目前已有基础提示词，你是一位Prompt优化师，旨在将用户输入的基础提示词改写为优质Prompt，使其更完整、更具表现力，同时不改变原意。

任务要求：
1. 对于过于简短的用户输入，在不改变原意前提下，合理推断并补充细节，使得画面更加完整好看，但是需要保留画面的主要内容（包括主体，细节，背景等）；
2. 完善用户描述中出现的主体特征（如外貌、表情，数量、种族、姿态等）、画面风格、空间关系、镜头景别；
3. 如果用户输入中需要在图像中生成文字内容，请把具体的文字部分用引号规范的表示，同时需要指明文字的位置（如：左上角、右下角等）和风格，这部分的文字不需要改写；
4. 如果需要在图像中生成的文字模棱两可，应该改成具体的内容，如：用户输入：邀请函上写着名字和日期等信息，应该改为具体的文字内容： 邀请函的下方写着“姓名：张三，日期： 2025年7月”；
5. 如果用户输入中要求生成特定的风格，应将风格保留。若用户没有指定，但画面内容适合用某种艺术风格表现，则应选择最为合适的风格。如：用户输入是古诗，则应选择中国水墨或者水彩类似的风格。如果希望生成真实的照片，则应选择纪实摄影风格或者真实摄影风格；
6. 如果Prompt是古诗词，应该在生成的Prompt中强调中国古典元素，避免出现西方、现代、外国场景；
7. 如果用户输入中包含逻辑关系，则应该在改写之后的prompt中保留逻辑关系。如：用户输入为“画一个草原上的食物链”，则改写之后应该有一些箭头来表示食物链的关系。
8. 改写之后的prompt中不应该出现任何否定词。如：用户输入为“不要有筷子”，则改写之后的prompt中不应该出现筷子。
9. 除了用户明确要求书写的文字内容外，**禁止增加任何额外的文字内容**。

改写示例：
1. 用户输入："一张学生手绘传单，上面写着：we sell waffles: 4 for _5, benefiting a youth sports fund。"
    改写输出："手绘风格的学生传单，上面用稚嫩的手写字体写着：“We sell waffles: 4 for $5”，右下角有小字注明"benefiting a youth sports fund"。画面中，主体是一张色彩鲜艳的华夫饼图案，旁边点缀着一些简单的装饰元素，如星星、心形和小花。背景是浅色的纸张质感，带有轻微的手绘笔触痕迹，营造出温馨可爱的氛围。画面风格为卡通手绘风，色彩明亮且对比鲜明。"
2. 用户输入："一张红金请柬设计，上面是霸王龙图案和如意云等传统中国元素，白色背景。顶部用黑色文字写着“Invitation”，底部写着日期、地点和邀请人。"
    改写输出："中国风红金请柬设计，以霸王龙图案和如意云等传统中国元素为主装饰。背景为纯白色，顶部用黑色宋体字写着“Invitation”，底部则用同样的字体风格写有具体的日期、地点和邀请人信息：“日期：2023年10月1日，地点：北京故宫博物院，邀请人：李华”。霸王龙图案生动而威武，如意云环绕在其周围，象征吉祥如意。整体设计融合了现代与传统的美感，色彩对比鲜明，线条流畅且富有细节。画面中还点缀着一些精致的中国传统纹样，如莲花、祥云等，进一步增强了其文化底蕴。"
3. 用户输入："一家繁忙的咖啡店，招牌上用中棕色草书写着“CAFE”，黑板上则用大号绿色粗体字写着“SPECIAL”"
    改写输出："繁华都市中的一家繁忙咖啡店，店内人来人往。招牌上用中棕色草书写着“CAFE”，字体流畅而富有艺术感，悬挂在店门口的正上方。黑板上则用大号绿色粗体字写着“SPECIAL”，字体醒目且具有强烈的视觉冲击力，放置在店内的显眼位置。店内装饰温馨舒适，木质桌椅和复古吊灯营造出一种温暖而怀旧氛围。背景中可以看到忙碌的咖啡师正在专注地制作咖啡，顾客们或坐或站，享受着咖啡带来的愉悦时光。整体画面采用纪实摄影风格，色彩饱和度适中，光线柔和自然。"
4. 用户输入："手机挂绳展示，四个模特用挂绳把手机挂在脖子上，上半身图。"
    改写输出："时尚摄影风格，四位年轻模特展示手机挂绳的使用方式，他们将手机通过挂绳挂在脖子上。模特们姿态各异但都显得轻松自然，其中两位模特正面朝向镜头微笑，另外两位则侧身站立，面向彼此交谈。模特们的服装风格多样但统一为休闲风，颜色以浅色系为主，与挂绳形成鲜明对比。挂绳本身设计简洁大方，色彩鲜艳且具有品牌标识。背景为简约的白色或灰色调，营造出现代而干净的感觉。镜头聚焦于模特们的上半身，突出挂绳和手机的细节。"
5. 用户输入："一只小女孩口中含着青蛙。"
    改写输出："一只穿着粉色连衣裙的小女孩，皮肤白皙，有着大大的眼睛和俏皮的齐耳短发，她口中含着一只绿色的小青蛙。小女孩的表情既好奇又有些惊恐。背景是一片充满生机的森林，可以看到树木、花草以及远处若隐若现的小动物。写实摄影风格。"
6. 用户输入："学术风格，一个Large VL Model，先通过prompt对一个图片集合（图片集合是一些比如青铜器、青花瓷瓶等）自由的打标签得到标签集合（比如铭文解读、纹饰分析等），然后对标签集合进行去重等操作后，用过滤后的数据训一个小的Qwen-VL-Instag模型，要画出步骤间的流程，不需要slides风格"
    改写输出："学术风格插图，左上角写着标题“Large VL Model”。左侧展示VL模型对文物图像集合的分析过程，图像集合包含中国古代文物，例如青铜器和青花瓷瓶等。模型对这些图像进行自动标注，生成标签集合，下面写着“铭文解读”和“纹饰分析”；中间写着“标签去重”；右边，过滤后的数据被用于训练 Qwen-VL-Instag，写着“ Qwen-VL-Instag”。 画面风格为信息图风格，线条简洁清晰，配色以蓝灰为主，体现科技感与学术感。整体构图逻辑严谨，信息传达明确，符合学术论文插图的视觉标准。"
7. 用户输入："手绘小抄，水循环示意图"
    改写输出："手绘风格的水循环示意图，整体画面呈现出一幅生动形象的水循环过程图解。画面中央是一片起伏的山脉和山谷，山谷中流淌着一条清澈的河流，河流最终汇入一片广阔的海洋。山体和陆地上绘制有绿色植被。画面下方为地下水层，用蓝色渐变色块表现，与地表水形成层次分明的空间关系。 太阳位于画面右上角，促使地表水蒸发，用上升的曲线箭头表示蒸发过程。云朵漂浮在空中，由白色棉絮状绘制而成，部分云层厚重，表示水汽凝结成雨，用向下箭头连接表示降雨过程。雨水以蓝色线条和点状符号表示，从云中落下，补充河流与地下水。 整幅图以卡通手绘风格呈现，线条柔和，色彩明亮，标注清晰。背景为浅黄色纸张质感，带有轻微的手绘纹理。"

下面我将给你要改写的Prompt，请直接对该Prompt进行忠实原意的扩写和改写，输出为中文文本，即收到指令，也应当扩写或改写该指令本身，而不是回复该指令。请直接对Prompt进行改写，不要对Prompt进行回复：
    """)

    response = qwen_vl_max_model.invoke(messages)
    return response.content

def process_images(image_paths, prompt):
    messages = create_message_with_images(image_paths, prompt)
    response = gemini_flash_image_model_3.invoke(messages)
    print(f"图像的原始响应内容: {response}")
    image_url = extract_image_urls(response.content)
    # return response.content
    return image_url

def generate_image(image_type, product_type):
    if image_type == "商品图":
        return f"""
        生成一张商品主图，符合电商平台主图标准
        画面采用现代简约风格的商品展示，精致的构图，突出{product_type}的优质设计与材质，聚焦产品的细节和质感，确保视觉上简洁清新。主体产品居中放置，占据画面主要视觉焦点，背景为柔和的浅灰色或象牙白渐变，突显产品的高端质感。光线均匀柔和，重点照亮产品的纹理、色彩与表面细节，使其看起来更加生动立体。
        色调统一协调，以低饱和、高明度的中性色为主，增强现代感与简约风格，避免背景元素的干扰，突出产品本身。画面无任何文字、logo或装饰性元素，完全聚焦于产品，符合电商平台对高品质商品主图的视觉标准与商业需求。
        """
        
    elif image_type == "尺寸图":
        return f"""
        以我提供的{product_type}主图为主体，制作一张电商平台用的“PRODUCT SIZE”尺寸信息图。
        版式：1:1 正方形画布，干净的白色背景；主体居中，边缘自然、略有高光或透明薄膜质感。
        顶部：大标题“PRODUCT SIZE”，字体粗体无衬线，高对比清晰。标题下方添加一条小图标装饰分隔线颜色与主题一致。
        周围边框：四角与边缘放置与主题匹配的装饰元素，形成漂亮但不抢主体的边框，风格统一、高清。
        尺寸标注：添加标准工程尺寸箭头线与刻度样式——底部水平箭头标注宽度“10inch”，右侧垂直箭头标注高度“12inch”；箭头线为黑色，端点清晰；文字全部大写或统一格式，易读。
        底部补充说明文字：“ High Quality Material: 50 Pcs”，字体清晰，与标题颜色协调。
        要求：整体看起来像亚马逊/Temu/速卖通的专业产品尺寸展示图；主体图案颜色不偏色、不变形；画面清晰、无水印、无乱码、无多余logo；排版留白舒适，信息居中对齐。
        """
        
    elif image_type == "商品展示图1":
        return f"""
        生成一张商品的展示图，底部增加功能标识横幅，包含“Food Grade”、“Easy to Clean”、“Safe&Non-toxic”、“Disposable”、“Party Supplies”五项，每项配对应图标，图标与文字颜色需与主图主题色协调。整体风格简洁专业，突出{product_type}卖点（例如设计、材质、适用场景等）。
        采用现代品牌产品展示页风格，构图布局经过精心设计，既平衡协调又富有视觉节奏感。背景融入微妙的品牌元素点缀，营造独特的品牌识别度。
        功能信息区域设计简洁现代，与主视觉完美融合，色彩过渡自然柔和，整体呈现专业、可信赖的产品推广格调，提升品牌形象和产品价值感。
        """
        
    elif image_type == "商品展示图2":
        return f"""
        生成一张商品的展示图，顶部为“WEIGHT UPGRADE”标题，下方说明文字“Premium Quality, Stronger Durability”（对于{product_type}可以修改为：“Premium Material, Stronger Durability”）。底部横向排列五个功能图标（Non-slip、More Solid、More Heat Resistant、Cut Resistant、Leak Proof），图标设计简洁且与主图色调一致。整体突出{product_type}的耐用性和实用场景。
        营造真实自然的使用场景氛围，生动展现产品在日常环境中的实用价值。场景设置富有生活气息，光影效果真实细腻，捕捉产品与环境的和谐互动。
        整体色调温暖自然，构图注重故事感和代入感，呈现高品质的生活风格摄影质感，让消费者能够直观感受到产品的实用美学生活方式。
        """
        
    elif image_type == "场景图1":
        return f"""
        生成一张带有{product_type}的使用场景图片
        呈现温馨雅致的节日餐桌氛围，桌上摆放着精美的{product_type}和其他相关产品，构图精心安排空间层次和视觉引导。光线柔和自然，色彩搭配协调舒适，营造令人愉悦的节日用餐环境。
        细节处理精致细腻，整体氛围轻松优雅，既突出产品（如{product_type}）又保持场景的真实感，符合现代电商对场景化营销图片的高标准视觉要求。
        """
        
    elif image_type == "场景图2":
        return f"""
        生成一张带有{product_type}的使用场景图片
        生动展现欢乐节日聚餐的热烈场景，构图富有动感和生活气息。通过人物互动的自然刻画和环境细节的精心布置，营造出浓厚的节日欢庆氛围。
        光影运用生动自然，色彩明快富有节日特色，整体风格真实亲切，具有强烈的场景代入感和情感共鸣，完美展现产品（如{product_type}）在欢乐聚会中的重要角色。
        """
        
    else:
        return ""




@router.post("/process_images_quality_one/",summary="单张高质量图片套图")
async def process_images_quality_one_endpoint(
    input_ref_image1: UploadFile = File(None),
    output_ref_image1: UploadFile = File(None),
    input_ref_image2: UploadFile = File(None),
    output_ref_image2: UploadFile = File(None),
    input_ref_image3: UploadFile = File(None),
    output_ref_image3: UploadFile = File(None),
    user_image: UploadFile = File(...),
    user_description: str = Form(""),
    image_type: Literal["商品图", "尺寸图", "商品展示图1", "商品展示图2", "场景图1", "场景图2"] = Form("商品图"),
):
    try:
        # 创建临时目录保存上传的图片
        with tempfile.TemporaryDirectory() as temp_dir:
            # 确定参考图片路径
            ref_image_paths = []
            
            # 统计已上传的参考图片数量和完整的输入-输出对数量
            uploaded_files = [input_ref_image1, output_ref_image1, input_ref_image2, 
                             output_ref_image2, input_ref_image3, output_ref_image3]
            uploaded_count = sum(1 for file in uploaded_files if file is not None)
            
            # 计算完整的输入-输出对数量
            pairs = []
            if input_ref_image1 and output_ref_image1:
                pairs.append((input_ref_image1, output_ref_image1))
            if input_ref_image2 and output_ref_image2:
                pairs.append((input_ref_image2, output_ref_image2))
            if input_ref_image3 and output_ref_image3:
                pairs.append((input_ref_image3, output_ref_image3))
            
            # 根据上传数量进行不同处理
            if uploaded_count == 0:
                # 上传数量为0，加载模板图片
                default_paths = load_default_images(image_type)
                if not default_paths:
                    return {
                        "code": 500,
                        "message": f"无法加载'{image_type}'类型的默认参考图片",
                        "data": []
                    }
                ref_image_paths = default_paths
            elif len(pairs) < 2:
                # 完整的输入-输出对数量少于2对，返回错误
                return {
                    "code": 500,
                    "message": f"请上传2-3对{image_type}参考图（每对包含一张输入图和一张输出图）",
                    "data": []
                }
            else:
                # 上传了2-3对完整的参考图片，处理上传的图片
                for i, (input_file, output_file) in enumerate(pairs):
                    # 保存输入参考图片
                    input_path = os.path.join(temp_dir, f"{image_type}_input_ref{i+1}.jpg")
                    with open(input_path, "wb") as buffer:
                        shutil.copyfileobj(input_file.file, buffer)
                    ref_image_paths.append(input_path)
                    
                    # 保存输出参考图片
                    output_path = os.path.join(temp_dir, f"{image_type}_output_ref{i+1}.jpg")
                    with open(output_path, "wb") as buffer:
                        shutil.copyfileobj(output_file.file, buffer)
                    ref_image_paths.append(output_path)
            
            # 保存用户图片
            user_image_path = os.path.join(temp_dir, "user_image.jpg")
            with open(user_image_path, "wb") as buffer:
                shutil.copyfileobj(user_image.file, buffer)
            
            # 构建提示词生成所需的图片路径列表
            # 确保参考图片路径列表不为空
            if not ref_image_paths:
                raise HTTPException(status_code=400, detail="参考图片加载失败")
            
            # 创建包含所有参考图片和用户图片的列表
            eg_image_paths = ref_image_paths.copy()
            eg_image_paths.append(user_image_path)
            
            # 更新提示词生成逻辑，适应不同数量的参考图片对
            if len(pairs) >= 3:
                eg_prompt = "图二是图一的转换后图片，图四是图三的转换后图片，图六是图五的转换后图片，图七是待处理图片"
            else:  # len(pairs) == 2
                eg_prompt = "图二是图一的转换后图片，图四是图三的转换后图片，图五是待处理图片"
            
            # 生成提示词
            generated_prompt = generate_prompt(eg_image_paths, eg_prompt)
            print(f"generated_prompt:\n {generated_prompt}")

            if user_description:
                print("根据用户输入修改提示词")
                add_user_description_prompt=f"""
                原始提示词：{generated_prompt}
                用户描述：{user_description}
                """
                print(f"add_user_description_prompt:\n {add_user_description_prompt}")
                generated_prompt=add_user_description(prompt=add_user_description_prompt)
                print(f"add_user_generated_prompt:\n {generated_prompt}")

            # 优化提示词
            polished_prompt = polish_prompt(eg_image_paths, generated_prompt)

            # 处理图片生成 - 只使用输出参考图片和用户图片
            # 提取奇数索引的图片（假设它们是输出参考图片）
            output_ref_images = [ref_image_paths[i] for i in range(1, len(ref_image_paths), 2)]
            input_images = output_ref_images + [user_image_path]
            
            final_prompt = polished_prompt + "\n"
            
            # 根据参考图片数量调整最终提示词
            if len(output_ref_images) >= 3:
                final_prompt += "图一图二图三是示例图，图四是待处理图片。请根据以上编辑指令，对图四进行编辑并生成一张图片"
            elif len(output_ref_images) >= 2:
                final_prompt += "图一图二是示例图，图四是待处理图片。请根据以上编辑指令，对图三进行编辑并生成一张图片"
            
            final_prompt += "，生成的图片中不能出现示例图中图案，注意，餐盘图案要与待处理图片一致，不要改变盘子的图案,最终图片的尺寸为1600*1600px,请确保生成完整的图像，而不仅仅是文字描述。"
            print(f"final_prompt:\n {final_prompt}")
            
            # 图片url
            image_url = process_images(input_images, final_prompt)

            if not image_url:
                return {
                    "code": 500,
                    "message": "图片生成失败，找不到url",
                    "data": []
                }
                # 返回图片URL列表
            return {
                "code": 200,
                "message": "图片生成成功",
                "data":{
                    "image_url": image_url,
                    "image_type": image_type
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        return {
                    "code": 500,
                    "message": f"处理失败: {str(e)}",
                    "data": []
                }


@router.post("/process_images_quality_parallel/",summary="多张高质量图片套图")
async def process_images_quality_parallel_endpoint(
        user_image: UploadFile = File(...),
):
    """
    使用线程池并行调用6次现有接口，同时生成6种类型的图片
    """

    def process_single_quality_image(temp_image_path: str, image_type: str):
        """处理单张图片的内部函数"""
        try:
            # 创建临时目录保存上传的图片
            with tempfile.TemporaryDirectory() as temp_dir:
                default_paths = load_default_images(image_type)
                if not default_paths:
                    return {
                        "code": 500,
                        "message": f"无法加载'{image_type}'类型的默认参考图片",
                        "data": []
                    }

                ref_image_paths = default_paths
                user_image_path = temp_image_path

                # 创建包含所有参考图片和用户图片的列表
                eg_image_paths = ref_image_paths.copy()
                eg_image_paths.append(user_image_path)

                eg_prompt = "图二是图一的转换后图片，图四是图三的转换后图片，图六是图五的转换后图片，图七是待处理图片"

                # 生成提示词
                generated_prompt = generate_prompt(eg_image_paths, eg_prompt)
                print(f"generated_prompt:\n {generated_prompt}")

                # 优化提示词
                polished_prompt = polish_prompt(eg_image_paths, generated_prompt)

                # 处理图片生成 - 只使用输出参考图片和用户图片
                output_ref_images = [ref_image_paths[i] for i in range(1, len(ref_image_paths), 2)]
                input_images = output_ref_images + [user_image_path]

                final_prompt = polished_prompt + "\n"
                final_prompt += "图一图二图三是示例图，图四是待处理图片。请根据以上编辑指令，对图四进行编辑并生成一张图片"
                final_prompt += "，生成的图片中不能出现示例图中图案，注意，餐盘图案要与待处理图片一致，不要改变盘子的图案,最终图片的尺寸为1600 * 1600px,请确保生成完整的图像，而不仅仅是文字描述。。"
                print(f"final_prompt:\n {final_prompt}")

                # 生成图片
                image_url = process_images(input_images, final_prompt)

                if not image_url:
                    return {
                        "code": 500,
                        "message": "图片生成失败，找不到url",
                        "data": []
                    }

                print(f"image_url: {image_url}, image_type: {image_type}")
                return {
                    "code": 200,
                    "message": "图片生成成功",
                    "data": {
                        "image_url": image_url,
                        "image_type": image_type
                    }
                }

        except Exception as e:
            print(f"处理图片类型 {image_type} 时发生异常: {str(e)}")
            return {
                "code": 500,
                "message": f"处理失败: {str(e)}",
                "data": []
            }

    # 主接口逻辑
    try:
        # 创建临时目录保存用户上传的图片
        with tempfile.TemporaryDirectory() as temp_dir:
            # 保存用户上传的图片到临时文件
            user_image_path = os.path.join(temp_dir, f"user_image_{uuid.uuid4().hex}.jpg")
            with open(user_image_path, "wb") as buffer:
                # 重置文件指针到开头
                await user_image.seek(0)
                shutil.copyfileobj(user_image.file, buffer)

            print(f"用户图片已保存到: {user_image_path}")

            # 定义6种图片类型
            image_types = [
                "商品图",
                "尺寸图",
                "商品展示图1",
                "商品展示图2",
                "场景图1",
                "场景图2"
            ]

            print(f"开始并行处理 {len(image_types)} 种图片类型...")

            # 使用线程池并行处理
            results = []
            with ThreadPoolExecutor(max_workers=6) as executor:
                # 提交所有任务
                futures = [
                    executor.submit(process_single_quality_image, user_image_path, image_type)
                    for image_type in image_types
                ]

                print(f"已提交 {len(futures)} 个任务")

                # 收集结果，设置超时
                for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                    try:
                        result = future.result(timeout=300)  # 每个任务最多300秒
                        results.append(result)
                        print(f"任务 {i}/{len(futures)} 完成")
                    except concurrent.futures.TimeoutError:
                        return {
                            "code": 500,
                            "message": "任务执行超时",
                            "data": []
                        }

            # 分析结果
            success_results = [
                r.get("data") for r in results
                if r.get('code') == 200
            ]

            print(f"成功生成 {len(success_results)} 张图片")

            if not success_results:
                return {
                    "code": 500,
                    "message": "所有图片生成都失败了",
                    "data": []
                }

            return {
                "code": 200,
                "message": f"图片生成成功（{len(success_results)}/{len(image_types)}）",
                "data": success_results
            }

    except HTTPException:
        raise
    except Exception as e:
        return {
            "code": 500,
            "message": f"并行处理异常: {str(e)}",
            "data": []
        }


@router.post("/process_images_fast_one/",summary="单张快速图片套图")
async def process_images_fast_one_endpoint(
        user_image: UploadFile = File(...),
        user_description: str = Form(""),
        image_type: Literal["商品图", "尺寸图", "商品展示图1", "商品展示图2", "场景图1", "场景图2"] = Form("商品图"),
):
    try:
        # 创建临时目录保存上传的图片
        with tempfile.TemporaryDirectory() as temp_dir:
            # 保存用户图片
            user_image_path = os.path.join(temp_dir, "user_image.jpg")
            with open(user_image_path, "wb") as buffer:
                shutil.copyfileobj(user_image.file, buffer)
            generated_prompt = info_template(image_type)
            if user_description:
                print("根据用户输入修改提示词")
                add_user_description_prompt = f"""
                原始提示词：{generated_prompt}
                用户描述：{user_description}
                """
                print(f"add_user_description_prompt:\n {add_user_description_prompt}")
                generated_prompt = add_user_description(prompt=add_user_description_prompt)
                print(f"add_user_generated_prompt:\n {generated_prompt}")
            final_prompt=generated_prompt+"\n注意，不要改变商品本身的图案,最终图片的尺寸为1600*1600px,请确保生成完整的图像，而不仅仅是文字描述。"
            # 图片url
            image_url = process_images([user_image_path], final_prompt)
            if not image_url:
                return {
                    "code": 500,
                    "message": "图片生成失败，找不到url",
                    "data": []
                }
                # 返回图片URL列表
            return {
                "code": 200,
                "message": "图片生成成功",
                "data": {
                    "image_url": image_url,
                    "image_type": image_type
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        return {
            "code": 500,
            "message": f"处理失败: {str(e)}",
            "data": []
        }


@router.post("/process_images_fast_parallel/",summary="多张快速图片套图")
async def process_images_fast_parallel_endpoint(
        user_image: UploadFile = File(...),
):
    """
    使用线程池并行调用6次现有接口，同时生成6种类型的图片
    """

    def process_single_fast_image(temp_image_path: str, image_type: str):
        """处理单张图片的内部函数"""
        try:
            # 创建临时目录保存上传的图片
            with tempfile.TemporaryDirectory() as temp_dir:
                # 保存用户图片
                user_image_path = temp_image_path
                generated_prompt = info_template(image_type)
                final_prompt = generated_prompt + "\n注意，不要改变盘子的图案,最终图片的尺寸为1600*1600px,请确保生成完整的图像，而不仅仅是文字描述。"
                # 图片url
                image_url = process_images([user_image_path], final_prompt)
                if not image_url:
                    return {
                        "code": 500,
                        "message": "图片生成失败，找不到url",
                        "data": []
                    }

                print(f"image_url: {image_url}, image_type: {image_type}")
                return {
                    "code": 200,
                    "message": "图片生成成功",
                    "data": {
                        "image_url": image_url,
                        "image_type": image_type
                    }
                }

        except Exception as e:
            print(f"处理图片类型 {image_type} 时发生异常: {str(e)}")
            return {
                "code": 500,
                "message": f"处理失败: {str(e)}",
                "data": []
            }

    # 主接口逻辑
    try:
        # 创建临时目录保存用户上传的图片
        with tempfile.TemporaryDirectory() as temp_dir:
            # 保存用户上传的图片到临时文件
            user_image_path = os.path.join(temp_dir, f"user_image_{uuid.uuid4().hex}.jpg")
            with open(user_image_path, "wb") as buffer:
                # 重置文件指针到开头
                await user_image.seek(0)
                shutil.copyfileobj(user_image.file, buffer)

            print(f"用户图片已保存到: {user_image_path}")

            # 定义6种图片类型
            image_types = [
                "商品图",
                "尺寸图",
                "商品展示图1",
                "商品展示图2",
                "场景图1",
                "场景图2"
            ]

            print(f"开始并行处理 {len(image_types)} 种图片类型...")

            # 使用线程池并行处理
            results = []
            with ThreadPoolExecutor(max_workers=6) as executor:
                # 提交所有任务
                futures = [
                    executor.submit(process_single_fast_image, user_image_path, image_type)
                    for image_type in image_types
                ]

                print(f"已提交 {len(futures)} 个任务")

                # 收集结果，设置超时
                for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                    try:
                        result = future.result(timeout=300)  # 每个任务最多300秒
                        results.append(result)
                        print(f"任务 {i}/{len(futures)} 完成")
                    except concurrent.futures.TimeoutError:
                        return {
                            "code": 500,
                            "message": "任务执行超时",
                            "data": []
                        }

            # 分析结果
            success_results = [
                r.get("data") for r in results
                if r.get('code') == 200
            ]

            print(f"成功生成 {len(success_results)} 张图片")

            if not success_results:
                return {
                    "code": 500,
                    "message": "所有图片生成都失败了",
                    "data": []
                }

            return {
                "code": 200,
                "message": f"图片生成成功（{len(success_results)}/{len(image_types)}）",
                "data": success_results
            }

    except HTTPException:
        raise
    except Exception as e:
        return {
            "code": 500,
            "message": f"并行处理异常: {str(e)}",
            "data": []
        }

app = FastAPI()

# 注册路由
app.include_router(router)
# 定义允许的源
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://120.26.254.236:3000",
    "http://192.168.31.51:3000"

]

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 使用定义的源列表
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8700)