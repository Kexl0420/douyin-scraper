#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrape_to_csv.py

Selenium + webdriver-manager 自动管理 ChromeDriver，
抓取抖音视频链接的博主昵称 & 抖音号，导出到 results.csv。
"""

import time
import json
import re
import csv
import requests

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def find_nickname_in_json(obj):
    if isinstance(obj, dict):
        if "nickname" in obj and isinstance(obj["nickname"], str):
            return obj["nickname"]
        for v in obj.values():
            r = find_nickname_in_json(v)
            if r:
                return r
    elif isinstance(obj, list):
        for item in obj:
            r = find_nickname_in_json(item)
            if r:
                return r
    return None

def get_user_info(video_url):
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)

    try:
        driver.get(video_url)
        time.sleep(3)

        # 抓昵称
        nick = None
        # A) __NEXT_DATA__
        try:
            s = driver.find_element(By.CSS_SELECTOR, "script#__NEXT_DATA__")
            data = json.loads(s.get_attribute("innerText"))
            nick = find_nickname_in_json(data)
        except Exception:
            pass

        # B) 头像 alt
        avatar = None
        if not nick:
            try:
                avatar = driver.find_element(By.CSS_SELECTOR, 'img[src*="aweme-avatar"]')
                nick = avatar.get_attribute("alt").strip()
            except Exception:
                pass

        # C) 备用 DOM
        if not nick:
            for sel in ("h3[data-e2e='user-name']", "h1[data-e2e='title']", ".user-info .nickname"):
                try:
                    t = driver.find_element(By.CSS_SELECTOR, sel).text.strip()
                    if t:
                        nick = t
                        break
                except Exception:
                    continue

        if not nick:
            raise RuntimeError("未拿到昵称")

        # 转到主页
        href = None
        if avatar:
            try:
                href = avatar.find_element(By.XPATH, "ancestor::a").get_attribute("href")
            except Exception:
                pass
        if not href:
            href = driver.find_element(By.CSS_SELECTOR, "h3[data-e2e='user-name']") \
                         .find_element(By.XPATH, "ancestor::a") \
                         .get_attribute("href")

        profile = href if href.startswith("http") else "https://www.douyin.com" + href
        driver.get(profile)
        time.sleep(3)

        # 抓抖音号
        try:
            sp = driver.find_element(By.CSS_SELECTOR, "span.TVGQz3SI")
        except Exception:
            sp = driver.find_element(By.XPATH, "//span[contains(text(),'抖音号')]")
        text = sp.text.strip()
        m = re.search(r"抖音号[:：]?\s*([A-Za-z0-9]+)", text)
        if not m:
            raise RuntimeError(f"从“{text}”提取失败")
        douyin_id = m.group(1)

        return nick, douyin_id

    finally:
        driver.quit()

def main():
    input_file = "video_urls.txt"
    output_file = "抖音抓取ID.csv"

    with open(input_file, "r", encoding="utf-8") as fin, \
         open(output_file, "w", encoding="utf-8", newline="") as fout:

        reader = (line.strip() for line in fin if line.strip())
        writer = csv.writer(fout)
        # 写表头
        writer.writerow(["视频链接", "昵称", "抖音号"])

        for url in reader:
            try:
                nick, did = get_user_info(url)
                writer.writerow([url, nick, did])
                print(f"{url} → 昵称: {nick}，抖音号: {did}")
            except Exception as e:
                writer.writerow([url, f"抓取失败：{e}", ""])
                print(f"{url} → 抓取失败：{e}")
            time.sleep(1)

    print(f"\n结果已保存到 {output_file}")

if __name__ == "__main__":
    main()