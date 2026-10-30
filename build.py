"""Build the Geneva 2061 website in French (at the root) and English (under /en/).

Reads content/ and data/, writes the complete static site into _site/.
Run:  python build.py   (add --strict to stop on problems)
"""
import copy
import unicodedata
import re
import shutil
import sys
from pathlib import Path

import markdown
import yaml
from jinja2 import ChainableUndefined, Environment, FileSystemLoader

ROOT = Path(__file__).parent
OUT = ROOT / "_site"
LANGS = ("fr", "en")
PREFIX = {"fr": "", "en": "en/"}
SECTION = {"fr": {"ideas": "idees", "about": "a-propos", "disclaimer": "mentions-legales"},
           "en": {"ideas": "ideas", "about": "about", "disclaimer": "disclaimer"}}
SHARED = ("theme", "readiness", "needs", "levers", "also_relevant", "sensitive")
problems = []


def load_yaml(path):
    p = ROOT / path
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_front_matter(path):
    p = ROOT / path
    if not p.exists():
        return {}, ""
    text = p.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def md(text):
    return markdown.markdown(text or "", extensions=["extra", "smarty"])


def fr_typo(s):
    """French typography: non-breaking spaces before : ; ? ! and inside « »."""
    s = re.sub(r" ([:;?!»%])", lambda m: ("\u00a0" if m.group(1) in ":»%" else "\u202f") + m.group(1), s)
    s = s.replace("« ", "«\u00a0")
    s = re.sub(r"(\d) (\d{3})\b", "\\1\u202f\\2", s)
    return s


def typo_all(obj):
    if isinstance(obj, str):
        return fr_typo(obj)
    if isinstance(obj, list):
        return [typo_all(x) for x in obj]
    if isinstance(obj, dict):
        return {k: (v if k in ("url", "id", "code", "theme", "status", "readiness") else typo_all(v)) for k, v in obj.items()}
    return obj


def main():
    ui = load_yaml("data/ui.yml")
    ui["fr"] = typo_all(ui["fr"])
    site = {"en": load_yaml("data/site.yml"), "fr": typo_all(load_yaml("data/site_fr.yml"))}
    # The Google Analytics ID is set once, in data/site.yml, and used for both languages.
    site["fr"]["google_analytics_id"] = site["en"].get("google_analytics_id", "")
    walk = {"en": load_yaml("data/walk.yml"), "fr": typo_all(load_yaml("data/walk_fr.yml"))}
    themes_en = load_yaml("data/themes.yml")["themes"]
    themes_fr_extra = {t["code"]: t for t in typo_all(load_yaml("data/themes_fr.yml")).get("themes", [])}
    levels = load_yaml("data/readiness.yml")["levels"]
    needs = load_yaml("data/needs.yml")

    readiness = {"en": {}, "fr": {}}
    for l in levels:
        readiness["en"][l["code"]] = dict(code=l["code"], label=l["label"], short=l.get("short", ""),
                                          missing=l["missing"], text=l["text"])
        readiness["fr"][l["code"]] = typo_all(dict(code=l["code"], label=l.get("label_fr", l["label"]),
                                                   short=l.get("short_fr", ""), missing=l.get("missing_fr", ""),
                                                   text=l.get("text_fr", l["text"])))
    need_group = {n: g["name"] for g in needs["groups"] for n in g["needs"]}
    need_fr = needs.get("french", {})

    # Themes per language, keyed by the English code
    themes = {"en": [], "fr": []}
    for t in themes_en:
        c = t["code"]
        themes["en"].append(dict(key=c, code=c, name=t["name"], covers=t.get("covers", ""),
                                 heading=t.get("heading", ""), intro_html=md(t.get("intro", "")), ideas=[]))
        x = themes_fr_extra.get(c, {})
        themes["fr"].append(dict(key=c, code=t.get("code_fr", c), name=fr_typo(t.get("name_fr", t["name"])),
                                 covers=x.get("covers", ""), heading=x.get("heading", ""),
                                 intro_html=md(x.get("intro", "")), ideas=[]))
    for lang in LANGS:
        for t in themes[lang]:
            t["sortkey"] = unicodedata.normalize("NFKD", t["name"]).encode("ascii", "ignore").decode().lower()
    tkey = {lang: {t["key"]: t for t in themes[lang]} for lang in LANGS}

    # Ideas: English files hold the shared fields; French files hold the French text
    fr_files = {}
    for path in sorted((ROOT / "content/idees").glob("*.md")):
        e, _ = load_front_matter(path.relative_to(ROOT))
        if e.get("id"):
            fr_files[e["id"]] = typo_all(e)
    pairs = []
    for path in sorted((ROOT / "content/ideas").glob("*.md")):
        e, _ = load_front_matter(path.relative_to(ROOT))
        if not e.get("id"):
            problems.append(f"{path.name}: missing code (id)")
            continue
        e.setdefault("theme", e["id"][:3])
        for key in ("also_relevant", "needs", "today_facts", "precedents", "path", "levers", "questions", "sources"):
            e[key] = e.get(key) or []
        if e["theme"] not in tkey["en"]:
            problems.append(f"{e['id']}: unknown theme code {e['theme']}")
            continue
        if e.get("readiness") not in readiness["en"]:
            problems.append(f"{e['id']}: readiness must be one of {', '.join(readiness['en'])}")
            e["readiness"] = "front"
        for n in e["needs"]:
            if n not in need_group:
                problems.append(f"{e['id']}: '{n}' is not in the Universal Human Needs list")
        e["also_relevant"] = [c for c in e["also_relevant"] if c in tkey["en"]]
        fr_id = tkey["fr"][e["theme"]]["code"] + e["id"][3:]
        f = fr_files.pop(fr_id, None)
        if f is None:
            problems.append(f"{e['id']}: no French version (content/idees/{fr_id}.md)")
        else:
            f = copy.deepcopy(f)
            for k in SHARED:
                f[k] = e.get(k)
            for key in ("today_facts", "precedents", "path", "questions", "sources"):
                f[key] = f.get(key) or []
            f["id"] = fr_id
        pairs.append((e, f))
    for leftover in fr_files:
        problems.append(f"{leftover}: French idea without an English version")

    def visible(idea):
        return idea is not None and idea.get("status", "draft") != "hidden"

    for e, f in pairs:
        e["key"] = e["id"]
        if f:
            f["key"] = e["id"]
        if visible(e):
            tkey["en"][e["theme"]]["ideas"].append(e)
        if visible(f):
            tkey["fr"][e["theme"]]["ideas"].append(f)
    for lang in LANGS:
        for t in themes[lang]:
            t["ideas"].sort(key=lambda i: i["id"])

    # Output
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "assets", OUT / "assets")
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True,
                      undefined=ChainableUndefined, trim_blocks=True, lstrip_blocks=True)

    def page_path(lang, kind, key=None):
        p = PREFIX[lang]
        if kind == "home":
            return p
        if kind == "themes":
            return p + "themes/"
        if kind == "theme":
            return p + "themes/" + tkey[lang][key]["code"].lower() + "/"
        if kind == "idea":
            return p + SECTION[lang]["ideas"] + "/" + key.lower() + "/"
        if kind == "about":
            return p + SECTION[lang]["about"] + "/"
        if kind == "grooters":
            return p + "grooters/"
        if kind == "disclaimer":
            return p + SECTION[lang]["disclaimer"] + "/"
        return p

    def write(lang, rel, template, alt, **ctx):
        depth = len([x for x in rel.split("/") if x])
        root = "../" * depth
        other = "en" if lang == "fr" else "fr"
        html = env.get_template(template).render(
            lang=lang, other=other, root=root, base=root + PREFIX[lang], alt=root + alt, t=ui[lang],
            site=site[lang], themes=themes[lang], tkey=tkey[lang], readiness=readiness[lang],
            readiness_levels=[readiness[lang][l["code"]] for l in levels], walk=walk[lang],
            need_name=(lambda n: need_fr.get(n, n)) if lang == "fr" else (lambda n: n),
            need_group=(lambda n: need_fr.get(need_group.get(n, ""), need_group.get(n, ""))) if lang == "fr"
            else (lambda n: need_group.get(n, "")),
            lever=lambda l: ui[lang]["levers"].get(l, l),
            theme_url=lambda key: root + page_path(lang, "theme", key),
            idea_url=lambda i: root + page_path(lang, "idea", i["id"]),
            **ctx)
        target = OUT / rel / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")

    pages = {"fr": {}, "en": {}}
    for lang in LANGS:
        other = "en" if lang == "fr" else "fr"
        write(lang, page_path(lang, "home"), "home.html", page_path(other, "home"), nav="walk")
        write(lang, page_path(lang, "themes"), "themes.html", page_path(other, "themes"), nav="themes",
              page_title=ui[lang]["themes_title"])
        for t in themes[lang]:
            write(lang, page_path(lang, "theme", t["key"]), "theme.html", page_path(other, "theme", t["key"]),
                  nav="themes", page_title=t["name"], th=t)
    for e, f in pairs:
        for lang, idea, counterpart in (("en", e, f), ("fr", f, e)):
            if not visible(idea):
                continue
            other = "en" if lang == "fr" else "fr"
            alt = (page_path(other, "idea", counterpart["id"]) if visible(counterpart)
                   else page_path(other, "theme", e["theme"]))
            write(lang, page_path(lang, "idea", idea["id"]), "idea.html", alt, nav="themes",
                  page_title=f"{idea['id']} {idea.get('title', '')}", description=idea.get("summary"),
                  e=idea, theme=tkey[lang][e["theme"]])

    about_src = {"en": "content/about.md", "fr": "content/fr/about.md"}
    grooters_src = {"en": "content/grooters.md", "fr": "content/fr/grooters.md"}
    for lang in LANGS:
        other = "en" if lang == "fr" else "fr"
        meta, body = load_front_matter(about_src[lang])
        if lang == "fr":
            meta, body = typo_all(meta), fr_typo(body)
        depth = len([x for x in page_path(lang, "about").split("/") if x])
        bridge = env.get_template("bridge.html").render(
            t=ui[lang], readiness_levels=[readiness[lang][l["code"]] for l in levels])
        html = re.sub(r"<p>\s*\[\[bridge-diagram\]\]\s*</p>|\[\[bridge-diagram\]\]", lambda m: bridge, md(body))
        write(lang, page_path(lang, "about"), "about.html", page_path(other, "about"), nav="about",
              page_title=meta.get("title", ui[lang]["nav_about"]), about={"title": meta.get("title", ""), "html": html})
        meta, body = load_front_matter(grooters_src[lang])
        if lang == "fr":
            meta, body = typo_all(meta), fr_typo(body)
        meta["html"] = md(body)
        write(lang, page_path(lang, "grooters"), "grooters.html", page_path(other, "grooters"), nav="grooters",
              page_title=meta.get("title", "Grooters"), page=meta)

    disclaimer_src = {"en": "content/disclaimer.md", "fr": "content/fr/disclaimer.md"}
    for lang in LANGS:
        other = "en" if lang == "fr" else "fr"
        meta, body = load_front_matter(disclaimer_src[lang])
        if not meta and not body:
            problems.append(f"Disclaimer page missing ({disclaimer_src[lang]})")
            continue
        if lang == "fr":
            meta, body = typo_all(meta), fr_typo(body)
        meta["html"] = md(body)
        write(lang, page_path(lang, "disclaimer"), "disclaimer.html", page_path(other, "disclaimer"),
              nav="disclaimer", page_title=meta.get("title", ui[lang]["footer_disclaimer"]), page=meta)

    n_en = sum(1 for e, f in pairs if visible(e))
    n_fr = sum(1 for e, f in pairs if visible(f))
    print(f"Built {n_fr} French and {n_en} English ideas in {len(themes_en)} themes into {OUT.name}/")
    if problems:
        print("\nPlease check:")
        for p in problems:
            print("  -", p)
        if "--strict" in sys.argv:
            sys.exit(1)


if __name__ == "__main__":
    main()
