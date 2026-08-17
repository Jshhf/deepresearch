import zipfile, re, os
d = os.environ.get("DOCX_SOURCE_DIR", "")
if not d:
    raise SystemExit("请先设置 DOCX_SOURCE_DIR 环境变量，指向包含 DeepResearch 源 docx 的目录")
src = os.path.join(d, [f for f in os.listdir(d) if f.startswith("DeepResearch") and f.endswith(".docx")][0])
z = zipfile.ZipFile(src)
names = z.namelist()
imgs = [n for n in names if n.startswith("word/media/")]
print("media files:", len(imgs), "bytes:", sum(z.getinfo(n).file_size for n in imgs))
xml = z.read("word/document.xml").decode("utf-8", "ignore")
texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml)
joined = "\n".join(t for t in texts if t.strip())
print("xml text chars:", len(joined))
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DeepResearch_main_docx_raw.txt")
with open(out, "w", encoding="utf-8") as f:
    f.write(joined)
print("saved to", out)
