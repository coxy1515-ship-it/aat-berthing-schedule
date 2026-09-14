# AAT combined berthing schedule

Shows the current AAT Appleton Dock and Webb Dock West berthing schedule PDFs
side by side on one page, always up to date.

## How it works

- `scripts/update_schedule.py` visits AAT's berthing schedule page, finds
  today's two PDF links, and rewrites `docs/index.html` to embed them.
- `.github/workflows/update.yml` runs that script every 20 minutes on
  GitHub's servers and commits the result automatically.
- `docs/index.html` is served for free by GitHub Pages as a public URL.

Nothing runs on your own computer or VPS - GitHub does it all.

## One-time setup

1. Create a new **public** repo on GitHub (private repos need a paid plan
   for Pages), e.g. `aat-berthing-schedule`.
2. Push everything in this folder to it:

   ```bash
   cd aat-berthing-schedule
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<repo-name>.git
   git push -u origin main
   ```

3. On GitHub: **Settings -> Pages** -> under "Build and deployment",
   set **Source** to "Deploy from a branch", branch **main**, folder **/docs**.
   Save.
4. GitHub will give you a URL like:

   ```
   https://<your-username>.github.io/<repo-name>/
   ```

   That's the live page. It may take a minute or two to go live the first time.
5. Trigger the first real update: go to the **Actions** tab -> "Update
   berthing schedule" -> **Run workflow**. After it finishes (about 30
   seconds), refresh the Pages URL and you should see today's two PDFs.

After that, it just runs itself every 20 minutes.

## Giving it to your friend

Once the Pages URL is live, send your friend this snippet to drop into his
site (replace the URL with your actual Pages URL):

```html
<iframe
  src="https://<your-username>.github.io/<repo-name>/"
  style="width: 100%; height: 900px; border: none;"
  title="AAT berthing schedule">
</iframe>
```

## If AAT changes their page layout

The scraper looks for links ending in `.pdf` whose link text mentions
"Appleton" or "Webb"/"WDW" and "berth". If AAT redesigns their site and
the Action starts failing, check the **Actions** tab for the error message -
it'll say which dock's PDF link it couldn't find, which is the fastest way to
spot what changed.

## Running it yourself, manually

```bash
pip install -r requirements.txt
python scripts/update_schedule.py
```

This rewrites `docs/index.html` locally so you can check it before pushing.
