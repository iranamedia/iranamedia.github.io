"""خبرنامه (bulletin/latest.json) را درون صفحه‌های تارنما می‌نشاند، میان BULLETIN-START و BULLETIN-END.
اجرا: python3 tools/json2page.py bulletin/latest.json _site/index.html _site/news.html"""
import html, json, re, sys

b = json.load(open(sys.argv[1], encoding="utf-8"))
e = html.escape
parts = [f'<div class="stamp">{e(b["stamp"])}</div>', "<section>"]
for it in b.get("items", []):
    parts.append(f'<article class="story"><h3>{e(it["title"])}</h3><p>{e(it.get("body", ""))}</p></article>')
parts.append("</section>")
src = [s for s in b.get("sources", []) if s.get("url")]
if src:
    parts.append('<footer class="sources"><h3>منابع</h3><ol>')
    parts += [f'<li><a href="{e(s["url"])}">{e(s.get("name") or s["url"])}</a></li>' for s in src]
    parts.append("</ol></footer>")
block = "<!--BULLETIN-START-->\n" + "\n".join(parts) + "\n<!--BULLETIN-END-->"
for page in sys.argv[2:]:
    t = open(page, encoding="utf-8").read()
    t2 = re.sub(r"<!--BULLETIN-START-->.*?<!--BULLETIN-END-->", lambda m: block, t, flags=re.S)
    open(page, "w", encoding="utf-8").write(t2)
    print(page, "updated" if t2 != t else "unchanged")
