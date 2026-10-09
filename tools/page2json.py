import sys, re, json, html
src = open(sys.argv[1], encoding='utf-8').read()
m = re.search(r'<!--BULLETIN-START-->(.*?)<!--BULLETIN-END-->', src, re.S)
b = m.group(1)
def txt(s): return html.unescape(re.sub(r'<[^>]+>', '', s)).strip()
stamp = txt(re.search(r'<div class="stamp">(.*?)</div>', b, re.S).group(1))
items = [{"title": txt(h), "body": txt(p)} for h, p in
         re.findall(r'<article[^>]*class="story"[^>]*>\s*<h3[^>]*>(.*?)</h3>\s*<p[^>]*>(.*?)</p>', b, re.S)]
assert stamp and items
json.dump({"stamp": stamp, "items": items}, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(stamp, len(items))
