"""Build the Geneva 2061 website.

Reads the content (content/ and data/) and writes a complete static site
into _site/. Run:  python build.py
"""
import re
import shutil
import sys
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, ChainableUndefined

ROOT = Path(__file__).parent
OUT = ROOT / "_site"


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_front_matter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def md(text):
    return markdown.markdown(text or "", extensions=["extra", "smarty"])


def main():
    problems = []
    site = load_yaml(ROOT / "data/site.yml")
    themes = load_yaml(ROOT / "data/themes.yml")["themes"]
    walk = load_yaml(ROOT / "data/walk.yml")
    levels = load_yaml(ROOT / "data/readiness.yml")["levels"]
    needs = load_yaml(ROOT / "data/needs.yml")
    readiness = {l["code"]: l for l in levels}
    need_group = {n: g["name"] for g in needs["groups"] for n in g["needs"]}
    themes_by_code = {t["code"]: t for t in themes}
    for t in themes:
        t["ideas"] = []
        t["intro_html"] = md(t.get("intro", ""))

    ideas = []
    for path in sorted((ROOT / "content/ideas").glob("*.md")):
        e, _ = load_front_matter(path)
        if not e.get("id"):
            problems.append(f"{path.name}: missing code (id)")
            continue
        e.setdefault("theme", e["id"][:3])
        e.setdefault("status", "draft")
        for key in ("also_relevant", "needs", "today_facts", "precedents", "path",
                    "levers", "questions", "sources"):
            e[key] = e.get(key) or []
        if e["theme"] not in themes_by_code:
            problems.append(f"{e['id']}: unknown theme code {e['theme']}")
            continue
        if e.get("readiness") not in readiness:
            problems.append(f"{e['id']}: readiness must be one of {', '.join(readiness)}")
            e["readiness"] = "front"
        for n in e["needs"]:
            if n not in need_group:
                problems.append(f"{e['id']}: '{n}' is not in the Universal Human Needs list")
        e["also_relevant"] = [c for c in e["also_relevant"] if c in themes_by_code]
        ideas.append(e)
        themes_by_code[e["theme"]]["ideas"].append(e)
    for t in themes:
        t["ideas"].sort(key=lambda e: e["id"])

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "assets", OUT / "assets")

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True,
                      undefined=ChainableUndefined, trim_blocks=True, lstrip_blocks=True)
    common = dict(site=site, themes=themes, themes_by_code=themes_by_code,
                  readiness=readiness, readiness_levels=levels, need_group=need_group, walk=walk)

    def write(rel_dir, template, **ctx):
        depth = len([p for p in rel_dir.split("/") if p])
        root = "../" * depth
        html = env.get_template(template).render(root=root, **common, **ctx)
        target = OUT / rel_dir / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")

    write("", "home.html", nav="walk")
    write("themes", "themes.html", nav="themes", page_title="Themes")
    for t in themes:
        write(f"themes/{t['code'].lower()}", "theme.html", nav="themes", page_title=t["name"], t=t)
    for e in ideas:
        write(f"ideas/{e['id'].lower()}", "idea.html", nav="themes",
              page_title=f"{e['id']} {e['title']}", description=e.get("summary"),
              e=e, theme=themes_by_code[e["theme"]])

    about, body = load_front_matter(ROOT / "content/about.md")
    bridge = env.get_template("bridge.html").render(root="../", **common)
    about_html = re.sub(r"<p>\s*\[\[bridge-diagram\]\]\s*</p>|\[\[bridge-diagram\]\]", lambda m: bridge, md(body))
    write("about", "about.html", nav="about", page_title=about.get("title", "About"),
          about={"title": about.get("title", "About"), "html": about_html})

    print(f"Built {len(ideas)} ideas in {len(themes)} themes into {OUT.name}/")
    if problems:
        print("\nPlease check:")
        for p in problems:
            print("  -", p)
        if "--strict" in sys.argv:
            sys.exit(1)


if __name__ == "__main__":
    main()
