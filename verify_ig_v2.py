#!/usr/bin/env python3
# Quick verify + get Page token (Claude fix)
import os, requests

def env_any(*names):
    for n in names:
        v = os.getenv(n)
        if v: return v.strip()
    return None

bot_token = env_any("FB_PAGE_ACCESS_TOKEN", "META_PAGE_TOKEN")
page_id = env_any("FB_PAGE_ID") or "Iranamedia"
page_id = page_id.split(',')[0].strip()  # take first if multiple

print(f"Bot/System User token present: {bool(bot_token)} len={len(bot_token) if bot_token else 0}")
print(f"Page ID: {page_id}")

if not bot_token:
    print("❌ No token - set FB_PAGE_ACCESS_TOKEN secret with System User token (Never expires)")
    exit(1)

# 1. Get Page token via /{PAGE_ID}?fields=access_token (Claude fix)
print(f"\n--- 1. Getting Page token via GET /{page_id}?fields=access_token ---")
r = requests.get(f"https://graph.facebook.com/v20.0/{page_id}", params={"fields":"access_token,name,id","access_token":bot_token}, timeout=20)
print(f"Status: {r.status_code}")
print(f"Body: {r.text[:1200]}")
if r.ok:
    j = r.json()
    page_token = j.get("access_token")
    if page_token:
        print(f"\n✅ FOUND PAGE TOKEN for {page_id}: {page_token[:30]}... (len {len(page_token)})")
        print(f"   Use this as FB_PAGE_ACCESS_TOKEN secret (not the System User token)")
    else:
        print(f"⚠️ No access_token in response, using System User token directly may still work if it has Full access")
else:
    print(f"❌ Failed to get Page token - check System User has Full access to Page {page_id} and App Irana Publisher")

# 2. Get IG business account ID
print(f"\n--- 2. Getting IG ID via GET /{page_id}?fields=instagram_business_account ---")
# Try with bot token and also try with page token if we got it
for t, label in [(bot_token, "bot_token"), (locals().get('page_token', ''), "page_token")]:
    if not t: continue
    print(f"\nTrying with {label}:")
    r2 = requests.get(f"https://graph.facebook.com/v20.0/{page_id}", params={"fields":"instagram_business_account,name","access_token":t}, timeout=20)
    print(f"Status: {r2.status_code} Body: {r2.text[:1200]}")
    if r2.ok:
        j2 = r2.json()
        ig = j2.get("instagram_business_account")
        if ig:
            print(f"\n✅✅✅ FOUND IG_USER_ID: {ig.get('id')} - Set secret IG_USER_ID={ig.get('id')}")
        else:
            print(f"⚠️ No instagram_business_account linked to {page_id} - link @iranamedia_ in Page Settings > Linked Accounts > Instagram")

print("\nDone. If IG_USER_ID found, add it as secret. If Page token found, update FB_PAGE_ACCESS_TOKEN secret with Page token (not System User token).")
