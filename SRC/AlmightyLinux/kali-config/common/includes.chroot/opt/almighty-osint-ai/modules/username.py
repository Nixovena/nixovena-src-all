from concurrent.futures import ThreadPoolExecutor, as_completed
from core import C, box, prompt, ok, warn, err, info, http_head, http_get

SITES = {
    "GitHub":        "https://github.com/{u}",
    "GitLab":        "https://gitlab.com/{u}",
    "Twitter/X":     "https://x.com/{u}",
    "Instagram":     "https://www.instagram.com/{u}/",
    "Reddit":        "https://www.reddit.com/user/{u}",
    "TikTok":        "https://www.tiktok.com/@{u}",
    "YouTube":       "https://www.youtube.com/@{u}",
    "Twitch":        "https://www.twitch.tv/{u}",
    "Steam":         "https://steamcommunity.com/id/{u}",
    "Pinterest":     "https://www.pinterest.com/{u}/",
    "Medium":        "https://medium.com/@{u}",
    "DevTo":         "https://dev.to/{u}",
    "HackerNews":    "https://news.ycombinator.com/user?id={u}",
    "Keybase":       "https://keybase.io/{u}",
    "Lobsters":      "https://lobste.rs/u/{u}",
    "Vimeo":         "https://vimeo.com/{u}",
    "SoundCloud":    "https://soundcloud.com/{u}",
    "Behance":       "https://www.behance.net/{u}",
    "Dribbble":      "https://dribbble.com/{u}",
    "ProductHunt":   "https://www.producthunt.com/@{u}",
    "Flickr":        "https://www.flickr.com/people/{u}",
    "Mastodon.social":"https://mastodon.social/@{u}",
    "DeviantArt":    "https://www.deviantart.com/{u}",
    "AboutMe":       "https://about.me/{u}",
    "Replit":        "https://replit.com/@{u}",
    "CodePen":       "https://codepen.io/{u}",
    "Bitbucket":     "https://bitbucket.org/{u}/",
    "HackerEarth":   "https://www.hackerearth.com/@{u}",
    "Last.fm":       "https://www.last.fm/user/{u}",
    "Quora":         "https://www.quora.com/profile/{u}",
    "Patreon":       "https://www.patreon.com/{u}",
    "Buymeacoffee":  "https://www.buymeacoffee.com/{u}",
    "Telegram":      "https://t.me/{u}",
    "Wikipedia":     "https://en.wikipedia.org/wiki/User:{u}",
    "AskFm":         "https://ask.fm/{u}",
    "Slideshare":    "https://www.slideshare.net/{u}",
    "Disqus":        "https://disqus.com/by/{u}/",
    "Pastebin":      "https://pastebin.com/u/{u}",
    "Gravatar":      "https://en.gravatar.com/{u}",
    "OpenStreetMap": "https://www.openstreetmap.org/user/{u}",
}


def _check(name, url):
    code, _ = http_head(url, timeout=8)
    if code in (0, 404):
        return name, url, False
    if 200 <= code < 400:
        return name, url, True
    if code in (403, 401, 429):
        body = http_get(url, timeout=8)
        if isinstance(body, str) and len(body) > 200:
            return name, url, True
        return name, url, None
    return name, url, False


def lookup(username, max_workers=20):
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_check, n, t.format(u=username)): n for n, t in SITES.items()}
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception:
                continue
    results.sort(key=lambda x: (0 if x[2] is True else (1 if x[2] is None else 2), x[0]))
    return results


def render(results):
    for name, url, status in results:
        if status is True:
            print(f"  {C.GREEN}[FOUND]{C.RESET}     {name:<18} {C.DIM}{url}{C.RESET}")
        elif status is None:
            print(f"  {C.YELLOW}[MAYBE]{C.RESET}     {name:<18} {C.DIM}{url}{C.RESET}")


def dispatch(ctx, target, render_out=True):
    if not target:
        return None, "empty target"
    results = lookup(target, max_workers=ctx.cfg.options.get("max_workers", 16))
    found = [r for r in results if r[2] is True]
    maybe = [r for r in results if r[2] is None]
    data = {
        "found": [{"site": r[0], "url": r[1]} for r in found],
        "maybe": [{"site": r[0], "url": r[1]} for r in maybe],
        "all":   [{"site": r[0], "url": r[1], "status": r[2]} for r in results],
    }
    summary = f"Username '{target}' found on {len(found)} sites, {len(maybe)} possible"
    if render_out:
        info(f"Probed {len(SITES)} platforms")
        render(results)
        print()
        ok(summary)
    ctx.session.add_finding("username", target, data, summary=summary)
    return data, summary


def run(ctx):
    box("Username Hunter", C.BR_CYN)
    u = prompt("Enter username")
    if not u:
        err("Username is empty")
        return
    dispatch(ctx, u)
