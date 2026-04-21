name: 🎨 Kleverz AI Design Bot

on:
  schedule:
    - cron: '0 8 * * 0'
  workflow_dispatch:

jobs:
  design-job:
    runs-on: ubuntu-latest
    timeout-minutes: 90

    steps:
      - name: 📥 تحميل الكود
        uses: actions/checkout@v4

      - name: 🐍 إعداد Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: 📦 تثبيت المكتبات
        run: pip install -r requirements.txt

      - name: 🚀 تشغيل البوت
        env:
          BASEROW_TOKEN: ${{ secrets.BASEROW_TOKEN }}
          IMGBB_API_KEY: ${{ secrets.IMGBB_API_KEY }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: python main.py
