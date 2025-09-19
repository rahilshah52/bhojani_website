Tailwind CSS — Production build instructions (PowerShell)

Why build:
- The CDN (`https://cdn.tailwindcss.com`) is convenient for development but not recommended for production.
- Building Tailwind produces a single optimized CSS file (purged of unused classes) that you serve from `static/css/tailwind.css`.

Prerequisites:
- Node.js and npm installed.
- From your project root (where `e:/bhojani_website` exists), open PowerShell.

Quick setup (one-time):
1. Initialize npm and install Tailwind CLI:

```powershell
cd e:\bhojani_website\clinic_website
npm init -y
npm install -D tailwindcss@latest postcss@latest autoprefixer@latest
npx tailwindcss init
```

2. Create an input CSS file at `clinic_website/assets/tailwind-input.css` with the following content:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

3. Build a production CSS file (one-time or as part of CI):

You can run the Tailwind CLI directly or use the included npm script.

```powershell
# Using npx directly
npx tailwindcss -i ./assets/tailwind-input.css -o ./static/css/tailwind.css --minify --content "./templates/**/*.html" "./**/*.py"

# Or use the npm script (recommended)
npm run build:css
```

Notes:
- Replace the `--content` globs with paths that include any files containing Tailwind classes (JS, HTML, templates, Python-rendered strings).
- For iterative development, run `npx tailwindcss -i ./assets/tailwind-input.css -o ./static/css/tailwind.css --watch`.

Serving:
- After building, ensure `templates/base.html` references `/static/css/tailwind.css` (the template is already configured to do this when `config.DEBUG` is false).

CI/Deployment:
- Add the build step to your CI pipeline before deploying static files.
- Optionally, use PurgeCSS or the Tailwind `content` option to ensure unused classes are removed.

Troubleshooting:
- If classes appear missing in production, widen the `--content` globs so Tailwind sees all files that contain class names.
- Ensure the Flask app sets `app.config['DEBUG']=False` in production so `base.html` serves the compiled CSS instead of the CDN.
