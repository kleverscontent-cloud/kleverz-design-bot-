#!/usr/bin/env python3
"""
🤖 Kleverz AI Design Bot
يعمل كل أحد 10:00 صباحاً (توقيت القاهرة)
يستخدم Gemini Imagen لتوليد الصور
"""

import os
import re
import time
import base64
import logging
import requests
from datetime import datetime
import google.generativeai as genai
from PIL import Image
import io

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
FIELD_PROMPT = "field_7484"   # AI_Design_Prompt
FIELD_DESIGN = "field_7488"   # Designs link
BASE_URL     = "https://baserow.kleverz.cloud"

# ==================
# إعداد Gemini
# ==================
genai.configure(api_key=GEMINI_API_KEY)

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
        logger.info(f"✅ تم تحديث الصف {row_id} في Baserow")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث الصف {row_id}: {e}")
        return False

# ============================================================
# 3. كشف اللغة وبناء البرومبت
# ============================================================
def detect_language(text):
    arabic = len(re.findall(r'[\u0600-\u06FF]', text))
    english = len(re.findall(r'[a-zA-Z]', text))
    total = arabic + english
    if total == 0:
        return "arabic"
    return "arabic" if arabic / total > 0.4 else "english"

def build_prompt(original, platform_key):
    lang = detect_language(original)
    p    = PLATFORMS[platform_key]

    if lang == "arabic":
        rtl_rules = """
[نظام اتجاه النص — مهم جداً]
- جميع النصوص العربية يجب أن تكون من اليمين إلى اليسار (RTL)
- محاذاة النص: يمين
- الكلمات العربية يجب أن تُقرأ بشكل طبيعي من اليمين لليسار
- لا تعكس الحروف العربية أبداً
- الأرقام تبقى من اليسار لليمين داخل السياق العربي
"""
    else:
        rtl_rules = """
[Text Direction]
- Left-to-Right (LTR) for all text
- Standard left-aligned layout
"""

    prompt = f"""
{rtl_rules}

أنشئ تصميم احترافي لمنصة {p['label']}
النسبة: {p['ratio']} ({p['w']}×{p['h']} بكسل)

المحتوى المطلوب:
{original}

المتطلبات:
- تصميم احترافي وعصري لوسائل التواصل الاجتماعي
- جودة عالية وألوان جذابة ومناسبة للمحتوى
- تسلسل هرمي واضح للعناصر البصرية
- النصوص واضحة ومقروءة تماماً
- إذا كان النص عربياً: من اليمين لليسار ومحاذاة يمين
- إذا كان النص إنجليزياً: من اليسار لليمين ومحاذاة يسار
- خلفية مناسبة للموضوع
- تصميم يجذب الانتباه ويحقق التفاعل
""".strip()

    return prompt

# ============================================================
# 4. توليد الصورة عبر Gemini Imagen
# ============================================================
def generate_image_gemini(prompt, platform_key):
    """توليد صورة باستخدام Gemini Imagen 3"""
    try:
        from google.generativeai import ImageGenerationModel

        model = ImageGenerationModel("imagen-3.0-generate-001")
        p = PLATFORMS[platform_key]

        result = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio=p["gemini_ratio"],
            safety_filter_level="block_only_high",
            person_generation="allow_adult",
        )

        if result.images:
            image = result.images[0]
            img_bytes = image._image_bytes
            logger.info(f"✅ تم توليد صورة {platform_key} بـ Gemini Imagen")
            return img_bytes
        else:
            logger.warning(f"⚠️ Gemini Imagen لم يُرجع صوراً لـ {platform_key}")
            return None

    except Exception as e:
        logger.warning(f"⚠️ Gemini Imagen فشل: {e} — جاري المحاولة بـ Gemini Flash...")
        return generate_image_gemini_flash(prompt, platform_key)

def generate_image_gemini_flash(prompt, platform_key):
    """بديل: توليد صورة باستخدام Gemini 2.0 Flash"""
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        p = PLATFORMS[platform_key]

        enhanced_prompt = f"""
Generate a high-quality social media design image.
Platform: {p['label']} - Ratio {p['ratio']} ({p['w']}x{p['h']}px)

{prompt}

Output: A complete, professional, ready-to-post social media image.
"""
        response = model.generate_content(
            enhanced_prompt,
            generation_config={"response_modalities": ["IMAGE", "TEXT"]},
        )

        for part in response.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                img_bytes = base64.b64decode(part.inline_data.data)
                logger.info(f"✅ تم توليد صورة {platform_key} بـ Gemini Flash")
                return img_bytes

        logger.error(f"❌ Gemini Flash لم يُرجع صورة لـ {platform_key}")
        return None

    except Exception as e:
        logger.error(f"❌ فشل Gemini Flash لـ {platform_key}: {e}")
        return None

# ============================================================
# 5. رفع الصورة على ImgBB
# ============================================================
def upload_to_imgbb(image_bytes, title):
    try:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        r = requests.post(
            "https://api.imgbb.com/1/upload",
            data={
                "key": IMGBB_API_KEY,
                "image": encoded,
                "name": title,
                "expiration": 0,
            },
            timeout=60
        )
        r.raise_for_status()
        result = r.json()
        if result.get("success"):
            url = result["data"]["url"]
            logger.info(f"✅ رُفعت الصورة: {url}")
            return url
        logger.error(f"❌ ImgBB رفض الرفع: {result}")
        return None
    except Exception as e:
        logger.error(f"❌ خطأ في رفع ImgBB: {e}")
        return None

# ============================================================
# 6. تنسيق روابط التصاميم
# ============================================================
def format_links(platform_urls):
    lines = ["📱 روابط التصاميم:\n"]
    for key, url in platform_urls.items():
        p = PLATFORMS[key]
        lines.append(f"🔗 {p['label']} ({p['ratio']} | {p['w']}×{p['h']}px)")
        lines.append(f"   {url}\n")
    lines.append(f"⏰ تاريخ التصميم: {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC")
    return "\n".join(lines)

# ============================================================
# 7. معالجة صف واحد كامل
# ============================================================
def process_row(row):
    row_id = row.get("id")
    prompt = row.get(FIELD_PROMPT, "").strip()

    if not prompt:
        logger.warning(f"⚠️ الصف {row_id}: لا يوجد برومبت — تخطي")
        return False

    logger.info(f"\n{'='*55}")
    logger.info(f"🎯 معالجة الصف {row_id}")
    logger.info(f"📝 البرومبت: {prompt[:100]}...")

    # علامة "جاري التصميم"
    update_row(row_id, "🔄 جاري التصميم... يُرجى الانتظار")

    platform_urls = {}
    lang = detect_language(prompt)
    logger.info(f"🌍 اللغة: {'عربي (RTL)' if lang == 'arabic' else 'إنجليزي (LTR)'}")

    for platform_key, platform_info in PLATFORMS.items():
        logger.info(f"\n  🎨 تصميم {platform_info['label']}...")

        full_prompt = build_prompt(prompt, platform_key)
        img_bytes   = generate_image_gemini(full_prompt, platform_key)

        if not img_bytes:
            logger.warning(f"  ⚠️ فشل توليد {platform_key} — تخطي")
            continue

        title = f"kleverz_r{row_id}_{platform_key}_{datetime.now().strftime('%Y%m%d')}"
        url   = upload_to_imgbb(img_bytes, title)

        if url:
            platform_urls[platform_key] = url

        time.sleep(3)   # تجنب Rate Limit

    if platform_urls:
        formatted = format_links(platform_urls)
        update_row(row_id, formatted)
        logger.info(f"\n🎉 الصف {row_id}: تم بنجاح! ({len(platform_urls)}/{len(PLATFORMS)} تصميم)")
        return True
    else:
        update_row(row_id, "❌ فشل التصميم — سيُعاد المحاولة الأسبوع القادم")
        return False

# ============================================================
# 8. الدالة الرئيسية
# ============================================================
def main():
    logger.info(f"\n{'🚀'*18}")
    logger.info(f"🚀 Kleverz AI Design Bot — بدء التشغيل")
    logger.info(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    logger.info(f"{'🚀'*18}\n")

    rows = get_new_rows()

    if not rows:
        logger.info("✨ لا توجد صفوف جديدة هذا الأسبوع — الجلسة انتهت")
        return

    logger.info(f"📊 إجمالي الصفوف للمعالجة: {len(rows)}\n")

    success = 0
    fail    = 0

    for i, row in enumerate(rows, 1):
        logger.info(f"\n[{i}/{len(rows)}] ══════════════════════════")
        try:
            if process_row(row):
                success += 1
            else:
                fail += 1
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع في الصف {row.get('id')}: {e}")
            fail += 1
        time.sleep(5)

    # التقرير النهائي
    logger.info(f"\n{'='*55}")
    logger.info(f"📋 التقرير النهائي:")
    logger.info(f"   ✅ نجح  : {success} صف")
    logger.info(f"   ❌ فشل  : {fail} صف")
    logger.info(f"   📊 إجمالي: {success + fail} صف")
    logger.info(f"{'='*55}\n")

if __name__ == "__main__":
    main()
