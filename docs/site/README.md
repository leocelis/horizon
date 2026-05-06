# GitHub Pages Setup

`docs/site/index.html` is the landing page for `https://leocelis.github.io/horizon` (or a custom domain).

## To enable GitHub Pages (requires your approval)

1. Go to **github.com/leocelis/horizon → Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main`, Folder: `/docs/site`
4. Click **Save**

The site will be live at `https://leocelis.github.io/horizon` within a few minutes.

> **Note:** GitHub Pages on a private repo requires a GitHub paid plan (Pro, Team, or Enterprise).
> Make the repo public first, or upgrade the plan, before enabling Pages.

## Custom domain (optional)

Once Pages is live, add a CNAME file:
```
horizon.leocelis.com
```

And create a CNAME DNS record: `horizon.leocelis.com` → `leocelis.github.io`

> The `horizon.leocelis.com` subdomain is currently pointed at the DigitalOcean
> MCP server. If you want to use it for the landing page instead, update the CNAME
> in DigitalOcean DNS to point to `leocelis.github.io`.
>
> Alternatively, pick a different subdomain for the landing page (e.g. `docs.horizon.leocelis.com`).
