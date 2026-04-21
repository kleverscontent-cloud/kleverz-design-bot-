#!/usr/bin/env python3
"""
🤖 Kleverz AI Design Bot
يعمل كل أحد 10:00 صباحاً (توقيت القاهرة)
يستخدم كل خانات Baserow لتوليد تصاميم احترافية
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

# ==================
# Baserow Config
# ==================
TABLE_ID = 774
BASE_URL = "https://baserow.kleverz.cloud"

# جميع الخانات بالـ Field IDs
FIELDS = {
    "day":            "field_7475",
    "date":           "field_7476",
    "day_name":       "field_7477",
    "platform":       "field_7478",
    "topic_category": "field_7479",
    "content_type":   "field_7480",
    "post_copy":      "field_7481",
    "hashtags":       "field_7482",
    "video_script":   "field_7483",
    "ai_prompt":      "field_7484",
    "infographic":    "field_7485",
    "visual_style":   "field_7486",
    "cta":            "field_7487",
    "designs_link":   "field_7488",
}

# ==================
# إعداد Gemini
# ==================
client = genai.Client(api_key=GEMINI_API_KEY)

# ==================
# مقاسات المنصات
# ==================
PLATFORM_CONFIGS = {
    "facebook": [
        {"key": "facebook_post",  "label": "فيسبوك بوست",    "ratio": "16:9", "w": 1200, "h": 630},
        {"key": "facebook_reel",  "label": "فيسبوك ريلز",    "ratio": "9:16", "w": 1080, "h": 1920},
    ],
    "instagram": [
        {"key": "instagram_post",  "label": "إنستجرام بوست", "ratio": "1:1",  "w": 1080, "h": 1080},
        {"key": "instagram_story", "label": "إنستجرام ستوري","ratio": "9:16", "w": 1080, "h": 1920},
    ],
    "linkedin": [
        {"key": "linkedin_post",  "label": "لينكدإن بوست",   "ratio": "16:9", "w": 1200, "h": 627},
    ],
    "tiktok": [
        {"key": "tiktok_cover",   "label": "تيك توك",        "ratio": "9:16", "w": 1080, "h": 1920},
    ],
    "x": [
        {"key": "twitter_post",   "label": "تويتر/X",        "ratio": "16:9", "w": 1600, "h": 900},
    ],
    "default": [
        {"key": "instagram_post",  "label": "إنستجرام بوست", "ratio": "1:1",  "w": 1080, "h": 1080},
        {"key": "facebook_post",   "label": "فيسبوك بوست",   "ratio": "16:9", "w": 1200, "h": 630},
    ],
}

# ==================
# أنماط التصميم
# ==================
VISUAL_STYLE_GUIDE = {
    "Minimalist Infographic": "clean minimalist infographic design, white background, simple icons, clear data visualization, modern sans-serif typography",
    "Real Photography":       "photorealistic professional photography style, high quality, cinematic lighting, corporate feel",
    "Motion Graphics":        "dynamic motion graphics style, vibrant colors, bold typography, energetic composition",
    "3D Illustration":        "modern 3D illustration style, soft shadows, isometric or perspective view, professional finish",
    "Animated":               "flat design animation style, bright colors, simple shapes, modern and clean",
}

# ============================================================
# 1. Baserow — جلب الصفوف الجديدة
# ============================================================
def get_new_rows():
    """جلب الصفوف التي فيها AI_Design_Prompt وخانة Designs link فارغة"""
    url = f"{BASE_URL}/api/database/rows/table/{TABLE_ID}/"
    headers = {"Authorization": f"Token {BASEROW_TOKEN}"}
    params = {
        "user_field_names": "false",
        "size": 100,
        f"filter__{FIELDS['ai_prompt']}__not_empty":  "true",
        f"filter__{FIELDS['designs_link']}__empty":   "true",
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
        r = requests.patch(
            url, headers=headers,
            json={FIELDS["designs_link"]: text},
            timeout=30
        )
        r.raise_for_status()
        logger.info(f"✅ تم تحديث الصف {row_id}")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث الصف {row_id}: {e}")
        return False

# ============================================================
# 3. استخراج بيانات الصف
# ============================================================
def extract_row_data(row):
    """استخراج كل بيانات الصف بشكل منظم"""
    return {
        "id":             row.get("id"),
        "day":            row.get(FIELDS["day"], ""),
        "date":           row.get(FIELDS["date"], ""),
        "day_name":       row.get(FIELDS["day_name"], ""),
        "platform":       row.get(FIELDS["platform"], "").strip().lower(),
        "topic_category": row.get(FIELDS["topic_category"], ""),
        "content_type":   row.get(FIELDS["content_type"], ""),
        "post_copy":      row.get(FIELDS["post_copy"], ""),
        "hashtags":       row.get(FIELDS["hashtags"], ""),
        "video_script":   row.get(FIELDS["video_script"], ""),
        "ai_prompt":      row.get(FIELDS["ai_prompt"], "").strip(),
        "infographic":    row.get(FIELDS["infographic"], "").strip(),
        "visual_style":   row.get(FIELDS["visual_style"], "").strip(),
        "cta":            row.get(FIELDS["cta"], "").strip(),
    }

# ============================================================
# 4. كشف اللغة
# ============================================================
def detect_language(text):
    arabic  = len(re.findall(r'[\u0600-\u06FF]', text))
    english = len(re.findall(r'[a-zA-Z]', text))
    total   = arabic + english
    if total == 0:
        return "arabic"
    return "arabic" if arabic / total > 0.4 else "english"

# ============================================================
# 5. بناء البرومبت الكامل من كل الخانات
# ============================================================
def build_full_prompt(data, platform_config):
    """بناء برومبت شامل يستخدم كل خانات الجدول"""

    # كشف اللغة
    combined_text = f"{data['ai_prompt']} {data['post_copy']} {data['infographic']}"
    lang = detect_language(combined_text)

    # تعليمات اتجاه النص
    if lang == "arabic":
        direction = """
[TEXT DIRECTION - CRITICAL]:
- ALL Arabic text MUST flow RIGHT-TO-LEFT (RTL)
- Text alignment: RIGHT
- Arabic words must be readable naturally from right to left
- DO NOT reverse or mirror Arabic letters
- Numbers stay left-to-right within Arabic context
"""
    else:
        direction = "[TEXT DIRECTION]: Left-to-Right (LTR), left-aligned."

    # النمط البصري
    style_key    = data["visual_style"]
    style_guide  = VISUAL_STYLE_GUIDE.get(style_key, "professional modern social media design")

    # مقاس المنصة
    p_label = platform_config["label"]
    p_ratio = platform_config["ratio"]
    p_w     = platform_config["w"]
    p_h     = platform_config["h"]

    # بناء قسم الإنفوجرافيك
    infographic_section = ""
    if data["infographic"] and data["infographic"].upper() != "N/A":
        infographic_section = f"""
[INFOGRAPHIC DATA - Must be displayed clearly in the design]:
{data['infographic']}
"""

    # بناء قسم الـ CTA
    cta_section = ""
    if data["cta"]:
        cta_section = f"""
[CALL TO ACTION - Must appear prominently]:
"{data['cta']}"
"""

    # بناء البرومبت الكامل
    prompt = f"""
{direction}

[PLATFORM]: {p_label}
[DIMENSIONS]: {p_ratio} ratio — {p_w}×{p_h}px
[VISUAL STYLE]: {style_guide}
[CONTENT TYPE]: {data['content_type']}
[TOPIC]: {data['topic_category']}

[MAIN DESIGN REQUEST]:
{data['ai_prompt']}

{infographic_section}
{cta_section}

[DESIGN REQUIREMENTS]:
- Professional, high-quality social media design
- Style: {style_key}
- Platform optimized for {p_label}
- Clear visual hierarchy with proper typography
- Colors and composition suited for {data['topic_category']}
- Arabic text: right-to-left, right-aligned
- English text: left-to-right, left-aligned
- All text must be perfectly readable
- Design should encourage engagement and action
""".strip()

    return prompt, lang

# ============================================================
# 6. تحديد منصات التصميم
# ============================================================
def get_platform_configs(platform_str):
    """تحديد مقاسات التصميم بناءً على المنصة"""
    platform_lower = platform_str.lower().strip()

    for key in PLATFORM_CONFIGS:
        if key in platform_lower:
            return PLATFORM_CONFIGS[key]

    # افتراضي لو المنصة مش معروفة
    logger.warning(f"⚠️ منصة غير معروفة: '{platform_str}' — سيتم استخدام الافتراضي")
    return PLATFORM_CONFIGS["default"]

# ============================================================
# 7. توليد الصورة — Gemini Imagen 3
# ============================================================
def generate_image(prompt, ratio):
    """توليد صورة باستخدام Gemini Imagen 3"""
    try:
        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=ratio,
                safety_filter_level="BLOCK_ONLY_HIGH",
                person_generation="ALLOW_ADULT",
            ),
        )
        if response.generated_images:
            img_bytes = response.generated_images[0].image.image_bytes
            logger.info(f"✅ Imagen 3 — تم التوليد بنجاح")
            return img_bytes
        logger.warning("⚠️ Imagen لم يُرجع صورة — جاري المحاولة بـ Flash")
        return generate_image_flash(prompt, ratio)

    except Exception as e:
        logger.warning(f"⚠️ Imagen فشل: {e} — جاري المحاولة بـ Flash")
        return generate_image_flash(prompt, ratio)

def generate_image_flash(prompt, ratio):
    """بديل: Gemini 2.0 Flash"""
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
                logger.info("✅ Gemini Flash — تم التوليد بنجاح")
                return img_bytes
        return None
    except Exception as e:
        logger.error(f"❌ Flash فشل: {e}")
        return None

# ============================================================
# 8. رفع الصورة على ImgBB
# ============================================================
def upload_imgbb(image_bytes, title):
    try:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        r = requests.post(
            "https://api.imgbb.com/1/upload",
            data={
                "key":        IMGBB_API_KEY,
                "image":      encoded,
                "name":       title,
                "expiration": 0,
            },
            timeout=60
        )
        r.raise_for_status()
        result = r.json()
        if result.get("success"):
            url = result["data"]["url"]
            logger.info(f"✅ رُفعت: {url}")
            return url
        logger.error(f"❌ ImgBB رفض: {result}")
        return None
    except Exception as e:
        logger.error(f"❌ خطأ ImgBB: {e}")
        return None

# ============================================================
# 9. تنسيق الروابط النهائية
# ============================================================
def format_links(platform_urls, data):
    lines = [
        f"📅 اليوم: {data['day']} — {data['day_name']} ({data['date']})",
        f"📱 المنصة: {data['platform'].upper()}",
        f"🎨 النمط: {data['visual_style']}",
        f"📌 الموضوع: {data['topic_category']}",
        "",
        "🔗 روابط التصاميم:",
        ""
    ]
    for label, url in platform_urls.items():
        lines.append(f"▶ {label}")
        lines.append(f"  {url}")
        lines.append("")
    lines.append(f"⏰ تاريخ التصميم: {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC")
    return "\n".join(lines)

# ============================================================
# 10. معالجة صف واحد كامل
# ============================================================
def process_row(row):
    data = extract_row_data(row)
    row_id = data["id"]

    if not data["ai_prompt"]:
        logger.warning(f"⚠️ الصف {row_id}: لا يوجد AI_Design_Prompt — تخطي")
        return False

    logger.info(f"\n{'='*60}")
    logger.info(f"🎯 الصف {row_id} | يوم {data['day']} | {data['platform'].upper()}")
    logger.info(f"📌 الموضوع: {data['topic_category']} | النوع: {data['content_type']}")
    logger.info(f"🎨 النمط: {data['visual_style']}")
    logger.info(f"📝 البرومبت: {data['ai_prompt'][:80]}...")
    if data["infographic"]:
        logger.info(f"📊 إنفوجرافيك: {data['infographic'][:60]}...")
    if data["cta"]:
        logger.info(f"📣 CTA: {data['cta']}")

    # علامة جاري التصميم
    update_row(row_id, "🔄 جاري التصميم... يُرجى الانتظار")

    # تحديد المنصات المطلوبة
    platform_configs = get_platform_configs(data["platform"])
    logger.info(f"📐 سيتم التصميم لـ {len(platform_configs)} مقاس")

    platform_urls = {}

    for p_config in platform_configs:
        logger.info(f"\n  🎨 تصميم {p_config['label']} ({p_config['ratio']})...")

        # بناء البرومبت الكامل
        full_prompt, lang = build_full_prompt(data, p_config)
        logger.info(f"  🌍 اللغة: {'عربي RTL' if lang == 'arabic' else 'إنجليزي LTR'}")

        # توليد الصورة
        img_bytes = generate_image(full_prompt, p_config["ratio"])

        if img_bytes:
            title = f"kleverz_r{row_id}_{p_config['key']}_{datetime.now().strftime('%Y%m%d')}"
            url   = upload_imgbb(img_bytes, title)
            if url:
                platform_urls[p_config["label"]] = url
        else:
            logger.warning(f"  ⚠️ فشل توليد {p_config['label']}")

        time.sleep(3)

    if platform_urls:
        update_row(row_id, format_links(platform_urls, data))
        logger.info(f"\n🎉 الصف {row_id}: {len(platform_urls)}/{len(platform_configs)} تصميم ✅")
        return True

    update_row(row_id, "❌ فشل التصميم — سيُعاد الأسبوع القادم")
    return False

# ============================================================
# 11. الدالة الرئيسية
# ============================================================
def main():
    logger.info(f"\n{'🚀'*15}")
    logger.info(f"🚀 Kleverz AI Design Bot — بدء التشغيل")
    logger.info(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    logger.info(f"{'🚀'*15}\n")

    rows = get_new_rows()

    if not rows:
        logger.info("✨ لا توجد صفوف جديدة هذا الأسبوع")
        return

    logger.info(f"📊 إجمالي الصفوف للمعالجة: {len(rows)}\n")

    success, fail = 0, 0

    for i, row in enumerate(rows, 1):
        logger.info(f"\n[{i}/{len(rows)}] ══════════════════════════════")
        try:
            if process_row(row):
                success += 1
            else:
                fail += 1
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع في الصف {row.get('id')}: {e}")
            fail += 1
        time.sleep(5)

    logger.info(f"\n{'='*60}")
    logger.info(f"📋 التقرير النهائي:")
    logger.info(f"   ✅ نجح  : {success} صف")
    logger.info(f"   ❌ فشل  : {fail} صف")
    logger.info(f"   📊 إجمالي: {success + fail} صف")
    logger.info(f"{'='*60}")

if __name__ == "__main__":
    main()
