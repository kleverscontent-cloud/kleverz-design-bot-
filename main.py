#!/usr/bin/env python3
"""
🤖 Kleverz AI Design Bot
يعمل كل أحد 10:00 صباحاً (توقيت القاهرة)
يستخدم Google Gemini (google-genai) لتوليد الصور
"""

import os
import re
import time
import base64
import logging
import requests
from datetime import datetime
from google import genai
from google.genai import types

# ==================
# إعداد Logging
# ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# ==================
# إعدادات من GitHub Secrets
# ==================
BASEROW_TOKEN  = os.environ["BASEROW_TOKEN"]
IMGBB_API_KEY  = os.environ["IMGBB_API_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

TABLE_ID     = 774
FIELD_PROMPT = "field_7484"
FIELD_DESIGN = "field_7488"
BASE_URL     = "https://baserow.kleverz.cloud"

# ==================
# إعداد Gemini Client
# ==================
client = genai.Client(api_key=GEMINI_API_KEY)

# ==================
# مقاسات المنصات
# ==================
PLATFORMS = {
    "instagram_post": {
        "label": "إنستجرام بوست",
        "ratio": "1:1",
        "w": 1080, "h": 1080,
        "gemini_ratio": "1:1"
    },
    "instagram_story": {
        "label": "إنستجرام ستوري / ريلز",
        "ratio": "9:16",
        "w": 1080, "h": 1920,
        "gemini_ratio": "9:16"
    },
    "facebook_post": {
        "label": "فيسبوك بوست",
        "ratio": "16:9",
        "w": 1200, "h": 630,
        "gemini_ratio": "16:9"
    },
    "twitter_post": {
        "label": "تويتر / X",
        "ratio": "16:9",
        "w": 1600, "h": 900,
        "gemini_ratio": "16:9"
    },
}

# ============================================================
# 1. Baserow — جلب الصفوف الجديدة
# ============================================================
def get_new_rows():
    url = f"{BASE_URL}/api/database/rows/table/{TABLE_ID}/"
    headers = {"Authorization": f"Token {BASEROW_TOKEN}"}
    params = {
        "user_field_names": "false",
        "size": 100,
        f"filter__{FIELD_PROMPT}__not_empty": "true",
        f"filter__{FIELD_DESIGN}__empty": "true",
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        rows = r.json().get("results", [])
        logger.info(f"✅ تم جلب {len(rows)} صف جديد من Baserow")
        return rows
    except Exception as e:
        logger.error(f"❌ خطأ في جلب الصفوف: {e}")
        return []

# ============================================================
# 2. Baserow — تحديث خانة Designs link
# ============================================================
def update_row(row_id, text):
    url = f"{BASE_URL}/api/database/rows/table/{TABLE_ID}/{row_id}/"
    headers = {
        "Authorization": f"Token {BASEROW_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        r = requests.patch(url, headers=headers, json={FIELD_DESIGN: text}, timeout=30)
        r.raise_for_status()
        logger.info(f"✅ تم تحديث الصف {row_id}")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث الصف {row_id}: {e}")
        return False

# ============================================================
# 3. كشف اللغة وبناء البرومبت
# ============================================================
def detect_language(text):
    arabic  = len(re.findall(r'[\u0600-\u06FF]', text))
    english = len(re.findall(r'[a-zA-Z]', text))
    total   = arabic + english
    if total == 0:
        return "arabic"
    return "arabic" if arabic / total > 0.4 else "english"

def build_prompt(original, platform_key):
    lang = detect_language(original)
    p    = PLATFORMS[platform_key]

    if lang == "arabic":
        direction = """
[اتجاه النص — مهم جداً]
- جميع النصوص العربية من اليمين إلى اليسار RTL
- محاذاة النص: يمين
- الكلمات العربية تُقرأ بشكل طبيعي من اليمين لليسار
- لا تعكس الحروف أبداً
"""
    else:
        direction = "[Text Direction] Left-to-Right (LTR), left-aligned."

    return f"""
{direction}
أنشئ تصميم احترافي لـ {p['label']} بنسبة {p['ratio']} ({p['w']}×{p['h']}px)

المحتوى:
{original}

المتطلبات:
- تصميم عصري واحترافي لوسائل التواصل الاجتماعي
- ألوان جذابة وتسلسل هرمي واضح
- نصوص واضحة ومقروءة
- عربي: RTL يمين | إنجليزي: LTR يسار
""".strip()

# ============================================================
# 4. توليد الصورة — Gemini Imagen 3
# ============================================================
def generate_image(prompt, platform_key):
    p = PLATFORMS[platform_key]
    try:
        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=p["gemini_ratio"],
                safety_filter_level="BLOCK_ONLY_HIGH",
                person_generation="ALLOW_ADULT",
            ),
        )
        if response.generated_images:
            img_bytes = response.generated_images[0].image.image_bytes
            logger.info(f"✅ تم توليد صورة {platform_key}")
            return img_bytes
        logger.warning(f"⚠️ Imagen لم يُرجع صورة لـ {platform_key}")
        return None

    except Exception as e:
        logger.warning(f"⚠️ Imagen فشل: {e} — جاري المحاولة بـ Gemini Flash...")
        return generate_image_flash(prompt, platform_key)

def generate_image_flash(prompt, platform_key):
    """بديل تلقائي: Gemini 2.0 Flash"""
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"]
            ),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                img_bytes = base64.b64decode(part.inline_data.data)
                logger.info(f"✅ تم توليد صورة {platform_key} بـ Flash")
                return img_bytes
        return None
    except Exception as e:
        logger.error(f"❌ Flash فشل كمان: {e}")
        return None

# ============================================================
# 5. رفع الصورة على ImgBB
# ============================================================
def upload_imgbb(image_bytes, title):
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
            logger.info(f"✅ رُفعت: {url}")
            return url
        return None
    except Exception as e:
        logger.error(f"❌ خطأ ImgBB: {e}")
        return None

# ============================================================
# 6. تنسيق الروابط
# ============================================================
def format_links(platform_urls):
    lines = ["📱 روابط التصاميم:\n"]
    for key, url in platform_urls.items():
        p = PLATFORMS[key]
        lines.append(f"🔗 {p['label']} ({p['ratio']} | {p['w']}×{p['h']}px)")
        lines.append(f"   {url}\n")
    lines.append(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC")
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
    logger.info(f"🎯 الصف {row_id}: {prompt[:80]}...")

    update_row(row_id, "🔄 جاري التصميم...")

    lang = detect_language(prompt)
    logger.info(f"🌍 {'عربي RTL' if lang == 'arabic' else 'إنجليزي LTR'}")

    platform_urls = {}
    for key in PLATFORMS:
        logger.info(f"  🎨 {PLATFORMS[key]['label']}...")
        full_prompt = build_prompt(prompt, key)
        img_bytes   = generate_image(full_prompt, key)

        if img_bytes:
            title = f"kleverz_r{row_id}_{key}_{datetime.now().strftime('%Y%m%d')}"
            url   = upload_imgbb(img_bytes, title)
            if url:
                platform_urls[key] = url
        time.sleep(3)

    if platform_urls:
        update_row(row_id, format_links(platform_urls))
        logger.info(f"🎉 الصف {row_id}: {len(platform_urls)}/{len(PLATFORMS)} تصميم ✅")
        return True

    update_row(row_id, "❌ فشل التصميم — سيُعاد الأسبوع القادم")
    return False

# ============================================================
# 8. الدالة الرئيسية
# ============================================================
def main():
    logger.info(f"\n{'🚀'*15}")
    logger.info(f"🚀 Kleverz AI Design Bot")
    logger.info(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    logger.info(f"{'🚀'*15}\n")

    rows = get_new_rows()
    if not rows:
        logger.info("✨ لا توجد صفوف جديدة")
        return

    success, fail = 0, 0
    for i, row in enumerate(rows, 1):
        logger.info(f"[{i}/{len(rows)}]")
        try:
            if process_row(row):
                success += 1
            else:
                fail += 1
        except Exception as e:
            logger.error(f"❌ {e}")
            fail += 1
        time.sleep(5)

    logger.info(f"\n{'='*50}")
    logger.info(f"✅ نجح: {success} | ❌ فشل: {fail}")
    logger.info(f"{'='*50}")

if __name__ == "__main__":
    main()
