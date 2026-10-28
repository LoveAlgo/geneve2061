# Geneva 2061

The website for the Geneva 2061 vision. Every idea is one small file in `content/ideas/` (for example `HEA-01.md`). Each time something is saved, GitHub rebuilds the site and publishes it automatically, usually within two minutes.

## Where things live

| What | File |
| --- | --- |
| One idea per file | `content/ideas/HEA-01.md` … |
| The About page | `content/about.md` |
| The 24 themes, with French names and codes | `data/themes.yml` |
| Verity’s walk on the home page | `data/walk.yml` |
| Title, copyright and footer | `data/site.yml` |
| The four “how far along” levels | `data/readiness.yml` |
| Universal Human Needs | `data/needs.yml` |
| Design and layout (no need to touch) | `templates/`, `assets/style.css`, `build.py` |

## One-time setup

1. **Create the repository.** On GitHub, create a new repository (for example `geneva2061`) and upload all these files, keeping the folders. The hidden files `.pages.yml` and `.github/workflows/deploy.yml` must be included: when uploading through the browser, drag the whole folder rather than selecting files, or press Cmd+Shift+. on a Mac to show hidden files.
2. **Turn on publishing.** In the repository, go to Settings → Pages, and under “Build and deployment” choose **GitHub Actions** as the source. The site appears at `https://<your-username>.github.io/geneva2061/` after the first build (see the Actions tab).
3. **Set up the editor.** Go to https://app.pagescms.org, sign in with your GitHub account and choose the repository. You then edit ideas, themes, the walk and the About page through forms in your browser; every save publishes the site.
4. **Own domain (optional).** Buy a domain (for example a .ch address, roughly CHF 10–20 a year), then enter it under Settings → Pages → Custom domain and follow GitHub’s instructions for the DNS records.

GitHub Pages requires the repository to be **public** on a free account, so the “Private notes” field of each idea can be read by anyone who looks at the repository. If you want the repository private, use Cloudflare Pages instead (free): connect the repository, set the build command to `pip install -r requirements.txt && python build.py` and the output folder to `_site`.

## Adding an idea

In Pages CMS, open **Ideas** → **Add an entry**. Fill in the code (e.g. `MOB-01`), title, theme, how far along, and the status:

- **Draft** shows only the title, summary and human needs, with “page in preparation”.
- **Ready** shows the full page.

Empty sections are simply left out, so a page can be filled in step by step.

## Checking before publishing (optional)

If you have Python installed: `pip install -r requirements.txt`, then `python build.py`. The site is written to `_site/`. The build also lists problems such as an unknown theme code or a need that is not in the Universal Human Needs list. To view it: `python -m http.server -d _site`, then open http://localhost:8000.
