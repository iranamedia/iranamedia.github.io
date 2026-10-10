"""بخش «پشتیبانی از رسانه ایرانا» را به صفحه‌های سایت می‌افزاید (پیش از انتشار).
داده از support.json می‌آید؛ راه‌های کمک مالی تنها اگر پر شده باشند نمایان می‌شوند.
هر یک از donations: {"label": "...", "url": "..."} یا {"label": "...", "value": "نشانی کیف پول"}"""
import html, json, sys
from pathlib import Path

MARK = "<!--SUPPORT-START-->"
CSS = """<style>
#support{max-width:760px;margin:36px auto 28px;padding:20px 18px;border:1px solid var(--line,rgba(224,180,82,.28));border-radius:14px;
background:rgba(18,36,90,.55);color:var(--ivory,#f5ecd6);font:15px/1.9 var(--font-body,Tahoma,sans-serif);direction:rtl;text-align:right}
#support h3{margin:0 0 6px;font-size:20px;color:var(--gold,#e0b452)}#support p{margin:4px 0 12px}
#support a.b,#support button.b{display:inline-block;margin:4px 0 4px 8px;padding:8px 14px;border-radius:999px;border:1px solid var(--gold,#e0b452);
color:var(--gold,#e0b452);background:transparent;text-decoration:none;font:inherit;cursor:pointer}
#support a.b:hover,#support button.b:hover{background:var(--gold,#e0b452);color:var(--night,#0a1530)}
#support code{display:block;direction:ltr;text-align:left;word-break:break-all;background:rgba(0,0,0,.25);padding:8px 10px;border-radius:8px;margin:4px 0 10px;font-size:13px}
</style>"""


def block(cfg):
    e = html.escape
    out = [MARK, CSS, '<section id="support">', f"<h3>{e(cfg['title'])}</h3>", f"<p>{e(cfg['intro'])}</p>"]
    out.append('<p><button class="b" id="supShare" type="button">همرسانی این رسانه</button>')
    for l in cfg.get("links", []):
        out.append(f'<a class="b" href="{e(l["url"])}" target="_blank" rel="noopener">{e(l["label"])}</a>')
    out.append("</p>")
    for d in cfg.get("donations", []):
        if d.get("url"):
            out.append(f'<p><a class="b" href="{e(d["url"])}" target="_blank" rel="noopener">{e(d["label"])}</a></p>')
        elif d.get("value"):
            out.append(f'<p>{e(d["label"])}:</p><code>{e(d["value"])}</code>')
    out.append("</section>")
    out.append("""<script>(function(){var b=document.getElementById('supShare');if(!b)return;b.onclick=function(){
var d={title:document.title,url:location.href};if(navigator.share){navigator.share(d).catch(function(){});}
else if(navigator.clipboard){navigator.clipboard.writeText(d.url);b.textContent='پیوند رونوشت شد';}};})();</script>""")
    out.append("<!--SUPPORT-END-->")
    return "\n".join(out)


def main(root):
    cfg = json.load(open("support.json", encoding="utf-8"))
    b = block(cfg)
    for name in ("index.html", "news.html", "app.html"):
        p = Path(root) / name
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8")
        if MARK in s:
            continue
        i = s.rfind("</body>")
        p.write_text(s[:i] + b + "\n" + s[i:] if i >= 0 else s + b, encoding="utf-8")
        print("support ->", p)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "_site")
