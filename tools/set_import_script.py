# Points every assets/models/*.glb.import at the vertex-colour post-import script.
import glob, os, re
ROOT = os.path.join(os.path.dirname(__file__), "..")
n = 0
for p in glob.glob(os.path.join(ROOT, "assets", "models", "*.glb.import")):
    s = open(p, encoding="utf-8").read()
    s2 = re.sub(r'import_script/path="[^"]*"', 'import_script/path="res://scripts/import/vertex_color_import.gd"', s)
    if s2 != s:
        open(p, "w", encoding="utf-8", newline="\n").write(s2)
        n += 1
print("updated", n)
