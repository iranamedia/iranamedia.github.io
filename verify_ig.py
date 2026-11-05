#!/usr/bin/env python3
import os, requests

def env_any(*names):
    for n in names:
        v = os.getenv(n)
        if v: return v.strip()
    return None

token = env_any("FB_PAGE_ACCESS_TOKEN", "META_PAGE_TOKEN", "META_PAGE_ACCESS_TOKEN")
page_ids_raw = env_any("FB_PAGE_ID", "META_PAGE_ID") or "Iranamedia,61595357222750"
page_ids = [p.strip() for p in page_ids_raw.split(',') if p.strip()]

print(f"Using token: {bool(token)} len={len(token) if token else 0}")
print(f"Checking pages: {page_ids}")

for pid in page_ids:
    try:
        url = f"https://graph.facebook.com/v20.0/{pid}"
        params = {"fields": "instagram_business_account,name", "access_token": token}
        r = requests.get(url, params=params, timeout=20)
        print(f"\n--- Page: {pid} ---")
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text[:1000]}")
        j = r.json()
        ig = j.get("instagram_business_account")
        if ig:
            print(f"✅ FOUND IG_USER_ID for {pid}: {ig.get('id')}")
        else:
            print(f"❌ No Instagram linked to {pid}")
    except Exception as e:
        print(f"Error {pid}: {e}")
