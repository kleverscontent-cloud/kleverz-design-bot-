#!/usr/bin/env python3
"""
🤖 Kleverz AI Design Bot
يعمل كل أحد 10:00 صباحاً (توقيت القاهرة)
"""

import os
import re
import time
import base64
import logging
import requests
from datetime import datetime
from openai import OpenAI

# ==================
# إعداد Logging
# ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# ==================
# إعدادات من Secrets
# ==================
BASEROW_TOKEN  = os.environ["BASEROW_TOKEN"]
IMGBB_API_KEY  = os.environ["IMGBB_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
TABLE_ID       = 774
FIELD_PROMPT   = "field_7484"   # AI_Design_Prompt
FIELD_DESIGNS  = "field_7488"   # Designs link
BASE_URL       = "https://baserow.kleverz.cloud"

# ==================
# مقاسات المنصات
# ==================
PLATFORMS = {
    "instagram_post":    {"size": "1024x1024", "ratio": "1:1",   "label": "إنستجرام بوست",    "w": 1080, "h": 1080},
    "instagram_story":   {"size": "1024x1792", "ratio": "9:16",  "label": "إنستجرام ستوري",   "w": 1080, "h": 1920},
    "facebook_post":     {"size": "1792x1024", "ratio": "16:9",  "label": "فيسبوك بوست",      "w": 1200, "h": 630},
    "twitter_post":      {"size": "1792x1024", "ratio": "16:9",  "label": "تويتر/X",           "w": 1600, "h": 900},
}

client = OpenAI(api_key=OPENAI_API_KEY)

# ============================================================
# 1. Baserow — جلب الصفوف
# ============================================================
def get_new_rows():
    url = f"{BASE_URL}/api/database/rows/table/{TABLE_ID}/"
    headers = {"Authorization": f"Token {BASEROW_TOKEN}"}
    params  = {
        "user_field_names": "false",
        "size": 100,
        f"filter__{FIELD_PROMPT}__not_empty": "true",
        f"filter__{FIELD_DESIGNS}__empty":    "true",
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        rows = r.json().get("results", [])
        logger.info(f"✅ تم جلب {len(rows)} صف جديد")
        return rows
    except Exception as e:
        logger.error(f"❌ خطأ في جلب الصفوف: {e}")
        return []

# ============================================================
# 2. Baserow — تحديث خانة Designs link
# ============================================================
def update_row(row_id, text):
    url     = f"{BASE_URL}/api/database/rows/table/{TABLE_ID}/{row_id}/"
    headers = {"Authorization": f"Token {BASEROW_TOKEN}", "Content-Type": "application/json"}
    try:
        r = requests.patch(url, headers=headers, json={FIELD_DESIGNS: text}, timeout=30)
        r.raise_for_status()
        logger.info(f"✅ تم تحديث الصف {row_id}")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث الصف {row_id}: {e}")
        return False

# ============================================================
# 3. كشف اللغة وإصلاح اتجاه النص
# ============================================================
def detect_language(text):
    arabic = len(re.findall(r'[\u0600-\u06FF]', text))
    english = len(re.findall(r'[a-zA-Z]', text))
    if arabic + english == 0:
        return "arabic"
    return "arabic" if arabic / (arabic + english) > 0.4 else "english"

def build_prompt(original_prompt, platform_key):
    lang     = detect_language(original_prompt)
    platform = PLATFORMS[platform_key]

    if lang == "arabic":
        direction = """
CRITICAL - TEXT DIRECTION RULES:
- ALL Arabic text MUST be written RIGHT-TO-LEFT (RTL)
- Arabic words must flow naturally from right to left
- Text alignment must be RIGHT-aligned
- Use proper Arabic font rendering
- DO NOT reverse Arabic letters
- Each Arabic word must be readable from right to left
- If there are numbers, keep them LTR within RTL context
"""
    else:
        direction = "Text direction: Left-to-Right (LTR). Standard English layout."

    return f"""
{direction}

Create a professional social media design for {platform['label']}.
Aspect ratio: {platform['ratio']} ({platform['w']}x{platform['h']}px)

Design request:
{original_prompt}

Requirements:
- High quality, modern, professional design
- Perfect text rendering and alignment
- Vibrant colors suitable for social media
- Clean layout with clear visual hierarchy
- All text must be perfectly readable
- Arabic text: right-to-left, right-aligned
- English text: left-to-right, left-aligned
""".strip()

# ============================================================
# 4. توليد الصورة عبر DALL-E 3
# ============================================================
def generate_image(prompt, size):
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        # تحميل الصورة
        img_data = requests.get(image_url, timeout=60).content
        logger.info(f"✅ تم توليد الصورة ({size})")
        return img_data
    except Exception as e:
        logger.error(f"❌ خطأ في توليد الصورة: {e}")
        return None

# ============================================================
# 5. رفع الصورة على ImgBB
# ============================================================
def upload_to_imgbb(image_bytes, title):
    try:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        r = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_API_KEY, "image": encoded, "name": title},
            timeout=60
        )
        r.raise_for_status()
        result = r.json()
        if result.get("success"):
            url = result["data"]["url"]
            logger.info(f"✅ تم الرفع على ImgBB: {url}")
            return url
        return None
    except Exception as e:
        logger.error(f"❌ خطأ في رفع الصورة: {e}")
        return None

# ============================================================
# 6. تنسيق الروابط النهائية
# ============================================================
def format_links(platform_urls):
    lines = ["📱 روابط التصاميم:\n"]
    for platform_key, url in platform_urls.items():
        info = PLATFORMS[platform_key]
        lines.append(f"🔗 {info['label']} ({info['ratio']} | {info['w']}×{info['h']}px)")
        lines.append(f"   {url}\n")
    lines.append(f"⏰ تاريخ التصميم: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(lines)

# ============================================================
# 7. معالجة صف واحد
# ============================================================
def process_row(row):
    row_id = row.get("id")
    prompt = row.get(FIELD_PROMPT, "").strip()

    if not prompt:
        return False

    logger.info(f"\n{'='*50}")
    logger.info(f"🎯 معالجة الصف {row_id}")
    logger.info(f"📝 البرومبت: {prompt[:80]}...")

    # وضع علامة جاري التصميم
    update_row(row_id, "🔄 جاري التصميم...")

    platform_urls = {}

    for platform_key, platform_info in PLATFORMS.items():
        logger.info(f"  🎨 تصميم {platform_info['label']}...")

        full_prompt  = build_prompt(prompt, platform_key)
        image_bytes  = generate_image(full_prompt, platform_info["size"])

        if not image_bytes:
            logger.warning(f"  ⚠️ فشل توليد {platform_key}")
            continue

        title = f"kleverz_row{row_id}_{platform_key}"
        url   = upload_to_imgbb(image_bytes, title)

        if url:
            platform_urls[platform_key] = url

        time.sleep(2)  # تجنب Rate Limit

    if platform_urls:
        formatted = format_links(platform_urls)
        update_row(row_id, formatted)
        logger.info(f"🎉 الصف {row_id}: تم بنجاح ({len(platform_urls)} تصميم)")
        return True
    else:
        update_row(row_id, "❌ فشل التصميم - سيُعاد المحاولة")
        return False

# ============================================================
# 8. الدالة الرئيسية
# ============================================================
def main():
    logger.info(f"\n{'🚀'*15}")
    logger.info(f"🚀 بدء Kleverz AI Design Bot")
    logger.info(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'🚀'*15}\n")

    rows = get_new_rows()

    if not rows:
        logger.info("✨ لا توجد صفوف جديدة هذا الأسبوع")
        return

    success, fail = 0, 0

    for i, row in enumerate(rows, 1):
        logger.info(f"\n[{i}/{len(rows)}]")
        try:
            if process_row(row):
                success += 1
            else:
                fail += 1
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع: {e}")
            fail += 1
        time.sleep(3)

    logger.info(f"\n{'='*50}")
    logger.info(f"📋 النتيجة النهائية:")
    logger.info(f"   ✅ نجح: {success}")
    logger.info(f"   ❌ فشل: {fail}")
    logger.info(f"{'='*50}")

if __name__ == "__main__":
    main()
