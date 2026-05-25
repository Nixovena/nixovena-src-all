from core import C, box, prompt, ok, warn, err, info, row, http_get


def github_profile(user):
    api = http_get(f"https://api.github.com/users/{user}", timeout=12)
    if not isinstance(api, dict) or api.get("message") == "Not Found":
        return None
    repos = http_get(f"https://api.github.com/users/{user}/repos?per_page=100&sort=updated", timeout=15)
    keys  = http_get(f"https://github.com/{user}.keys", timeout=10)
    return {
        "profile":  api,
        "repos":    repos if isinstance(repos, list) else [],
        "ssh_keys": keys.splitlines() if isinstance(keys, str) and keys.strip() else [],
    }


def reddit_profile(user):
    r = http_get(f"https://www.reddit.com/user/{user}/about.json",
                 headers={"User-Agent": "AlmightyOSINTAI"}, timeout=12)
    return r["data"] if isinstance(r, dict) and "data" in r else None


def reddit_recent(user, limit=10):
    r = http_get(f"https://www.reddit.com/user/{user}.json?limit={limit}",
                 headers={"User-Agent": "AlmightyOSINTAI"}, timeout=12)
    if isinstance(r, dict) and "data" in r:
        return [c.get("data", {}) for c in r["data"].get("children", [])]
    return []


def hn_profile(user):
    r = http_get(f"https://hacker-news.firebaseio.com/v0/user/{user}.json", timeout=10)
    return r if isinstance(r, dict) and r.get("id") else None


def mastodon_lookup(handle):
    if "@" not in handle:
        return None
    user, _, host = handle.lstrip("@").partition("@")
    if not host:
        return None
    r = http_get(f"https://{host}/api/v1/accounts/lookup?acct={user}", timeout=10)
    return r if isinstance(r, dict) and r.get("id") else None


def dispatch(ctx, target, platform="github", render_out=True):
    t = (target or "").strip()
    if not t:
        if render_out: err("Empty target")
        return None, "empty"
    platform = (platform or "github").lower()

    if platform == "github":
        d = github_profile(t)
        if not d:
            if render_out: err("User not found")
            return None, "not found"
        p = d["profile"]
        recent_repos = sorted(d["repos"], key=lambda x: -x.get("stargazers_count", 0))[:8]
        data = {"platform": "github", "profile": p, "ssh_keys": d["ssh_keys"], "top_repos": recent_repos}
        summary = f"GitHub {t}: {p.get('public_repos',0)} repos, {p.get('followers',0)} followers"
        if render_out:
            row("Login",         p.get("login","?"))
            row("Name",          p.get("name") or "?")
            row("Bio",           (p.get("bio") or "")[:100])
            row("Email",         p.get("email") or "?")
            row("Location",      p.get("location") or "?")
            row("Company",       p.get("company") or "?")
            row("Blog",          p.get("blog") or "?")
            row("Twitter",       p.get("twitter_username") or "?")
            row("Followers",     str(p.get("followers", 0)))
            row("Public Repos",  str(p.get("public_repos", 0)))
            row("Created",       p.get("created_at","?"))
            row("SSH keys",      str(len(d["ssh_keys"])))
            if recent_repos:
                info("Top repos by stars:")
                for r in recent_repos:
                    print(f"    {C.CYAN}- {r['name']:<28}{C.RESET} {C.YELLOW}{r.get('stargazers_count',0)}*{C.RESET} {C.DIM}{(r.get('description','') or '')[:60]}{C.RESET}")
        ctx.session.add_finding("social-github", t, data, summary=summary)
        return data, summary

    if platform == "reddit":
        prof = reddit_profile(t)
        if not prof:
            if render_out: err("User not found / private")
            return None, "not found"
        recent = reddit_recent(t)
        data = {"platform": "reddit", "profile": prof, "recent": recent}
        summary = f"Reddit u/{t}: {prof.get('link_karma',0)}+{prof.get('comment_karma',0)} karma"
        if render_out:
            row("Username",        prof.get("name","?"))
            row("Created",         str(prof.get("created_utc","?")))
            row("Link Karma",      str(prof.get("link_karma",0)))
            row("Comment Karma",   str(prof.get("comment_karma",0)))
            row("Verified email",  str(prof.get("has_verified_email", False)))
            row("Gold",            str(prof.get("is_gold", False)))
            if recent:
                info("Recent activity:")
                for c in recent[:8]:
                    sub = c.get("subreddit","?")
                    body = (c.get("body") or c.get("title") or "")[:80]
                    print(f"    {C.CYAN}r/{sub:<14}{C.RESET} {C.DIM}{body}{C.RESET}")
        ctx.session.add_finding("social-reddit", t, data, summary=summary)
        return data, summary

    if platform == "hn" or platform == "hackernews":
        d = hn_profile(t)
        if not d:
            if render_out: err("User not found")
            return None, "not found"
        data = {"platform": "hn", "profile": d}
        summary = f"HN {t}: karma={d.get('karma',0)}"
        if render_out:
            row("ID",        d.get("id","?"))
            row("Karma",     str(d.get("karma",0)))
            row("Created",   str(d.get("created","?")))
            row("About",     (d.get("about") or "")[:200])
            row("Submitted", str(len(d.get("submitted",[]))))
        ctx.session.add_finding("social-hn", t, data, summary=summary)
        return data, summary

    if platform == "mastodon":
        d = mastodon_lookup(t)
        if not d:
            if render_out: err("Not found")
            return None, "not found"
        data = {"platform": "mastodon", "profile": d}
        summary = f"Mastodon {t}"
        if render_out:
            row("Username",  d.get("username","?"))
            row("Display",   d.get("display_name","?"))
            row("URL",       d.get("url","?"))
            row("Bio",       (d.get("note") or "")[:200])
            row("Followers", str(d.get("followers_count", 0)))
            row("Posts",     str(d.get("statuses_count", 0)))
        ctx.session.add_finding("social-mastodon", t, data, summary=summary)
        return data, summary

    if render_out: err(f"Unknown platform: {platform}")
    return None, "unknown platform"


def run(ctx):
    box("Social Media Snapshot", C.BR_MAG)
    print(f"  {C.DIM}1) GitHub  2) Reddit  3) HackerNews  4) Mastodon (@user@host){C.RESET}\n")
    choice = prompt("Pick", "1")
    handle = prompt("Username / handle")
    platform_map = {"1":"github","2":"reddit","3":"hn","4":"mastodon"}
    dispatch(ctx, handle, platform=platform_map.get(choice, "github"))
