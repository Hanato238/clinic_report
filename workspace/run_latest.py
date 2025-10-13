import json, subprocess, shlex

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return p.stdout.strip()

# ① 一番新しいディレクトリ＋PDF（ルート配下から取得）
info = json.loads(run(["tricho-pipeline", "newest-with-pdf", "."]))
base_dir = info["newest_dir"]
pdf = info["newest_pdf"]
print(f"Base dir : {base_dir}")
print(f"Base PDF : {pdf}")

# ② そのディレクトリ内で最新のサブディレクトリを取得（JSON群があるはず）
json_dir = run(["tricho-pipeline", "newest", base_dir])
print(f"JSON dir : {json_dir}")

# ③ Node.js経由でPDF生成
cmd = [
    "tricho-pipeline", "run-render", json_dir, pdf,
    "--render-js", "/path/to/render.js",
    "--html", "/path/to/template.html"
]
print("\n▶ Running:", " ".join(shlex.quote(c) for c in cmd))
subprocess.run(cmd, check=True)
