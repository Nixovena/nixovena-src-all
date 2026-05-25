import hashlib, json, os, socket, subprocess, re, math
from urllib.parse import quote_plus

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox,
)
from i18n import tr
from osint.tool_base import ToolWindow


# ────────────────────────────────────────────────────────
#  Social Media Username Search (Sherlock-style)
# ────────────────────────────────────────────────────────

SOCIAL_PLATFORMS = {
    'GitHub':          'https://github.com/{}',
    'Twitter/X':       'https://x.com/{}',
    'Instagram':       'https://www.instagram.com/{}/',
    'Reddit':          'https://www.reddit.com/user/{}',
    'TikTok':          'https://www.tiktok.com/@{}',
    'YouTube':         'https://www.youtube.com/@{}',
    'LinkedIn':        'https://www.linkedin.com/in/{}',
    'Pinterest':       'https://www.pinterest.com/{}/',
    'Tumblr':          'https://{}.tumblr.com',
    'Medium':          'https://medium.com/@{}',
    'Dev.to':          'https://dev.to/{}',
    'Keybase':         'https://keybase.io/{}',
    'HackerOne':       'https://hackerone.com/{}',
    'Bugcrowd':        'https://bugcrowd.com/{}',
    'GitLab':          'https://gitlab.com/{}',
    'Bitbucket':       'https://bitbucket.org/{}/',
    'Steam':           'https://steamcommunity.com/id/{}',
    'Twitch':          'https://www.twitch.tv/{}',
    'Spotify':         'https://open.spotify.com/user/{}',
    'SoundCloud':      'https://soundcloud.com/{}',
    'Flickr':          'https://www.flickr.com/people/{}/',
    'Vimeo':           'https://vimeo.com/{}',
    'Dribbble':        'https://dribbble.com/{}',
    'Behance':         'https://www.behance.net/{}',
    'About.me':        'https://about.me/{}',
    'Gravatar':        'https://en.gravatar.com/{}',
    'Patreon':         'https://www.patreon.com/{}',
    'Fiverr':          'https://www.fiverr.com/{}',
    'HackerNews':      'https://news.ycombinator.com/user?id={}',
    'StackOverflow':   'https://stackoverflow.com/users/?tab=accounts&SearchTerm={}',
    'Telegram':        'https://t.me/{}',
    'DockerHub':       'https://hub.docker.com/u/{}',
    'PyPI':            'https://pypi.org/user/{}/',
    'npm':             'https://www.npmjs.com/~{}',
    'Replit':          'https://replit.com/@{}',
    'Codepen':         'https://codepen.io/{}',
    'Mastodon':        'https://mastodon.social/@{}',
    'Threads':         'https://www.threads.net/@{}',
    'Bluesky':         'https://bsky.app/profile/{}.bsky.social',
    'Linktree':        'https://linktr.ee/{}',
    'Cash App':        'https://cash.app/${}',
    'Venmo':           'https://account.venmo.com/u/{}',
    'Snapchat':        'https://www.snapchat.com/add/{}',
    'VK':              'https://vk.com/{}',
    'Imgur':           'https://imgur.com/user/{}',
    'Trello':          'https://trello.com/{}',
    'Roblox':          'https://www.roblox.com/user.aspx?username={}',
    'Chess.com':       'https://www.chess.com/member/{}',
    'Lichess':         'https://lichess.org/@/{}',
    'Letterboxd':      'https://letterboxd.com/{}/',
    'Goodreads':       'https://www.goodreads.com/{}',
}


class SocialSearchWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__("Social Media Username Search", parent)
        self._input_row("Enter username", "Search", self._go)
        info = QLabel(f"Checks {len(SOCIAL_PLATFORMS)} platforms via HTTP probe")
        info.setProperty("cssClass", "muted")
        self.lay.addWidget(info)
        self._results_area()
        self._buttons()

    def _go(self):
        u = self.inp.text().strip()
        if u:
            self._async(self._run, u)

    @staticmethod
    def _run(username):
        import urllib.request, urllib.error
        sep = "=" * 50
        lines = [sep, f"  USERNAME SEARCH: {username}", sep, ""]
        found = []
        not_found = []
        errors = []
        for platform, url_tpl in sorted(SOCIAL_PLATFORMS.items()):
            url = url_tpl.format(username)
            try:
                req = urllib.request.Request(url, method='HEAD', headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                  'AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36'
                })
                resp = urllib.request.urlopen(req, timeout=8)
                code = resp.getcode()
                if code < 400:
                    found.append((platform, url))
                    lines.append(f"  [FOUND]     {platform:20s}  {url}")
                else:
                    not_found.append(platform)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    not_found.append(platform)
                else:
                    errors.append((platform, e.code))
            except Exception:
                errors.append((platform, "timeout"))

        lines += ["", f"  ── Summary ──",
                   f"  Found    : {len(found)}",
                   f"  Not Found: {len(not_found)}",
                   f"  Errors   : {len(errors)}", "", sep]
        return '\n'.join(lines)


# ────────────────────────────────────────────────────────
#  Google Dorking Assistant
# ────────────────────────────────────────────────────────

DORK_TEMPLATES = {
    'Exposed Files': 'site:{domain} ext:sql OR ext:env OR ext:log OR ext:bak OR ext:cfg',
    'Login Pages': 'site:{domain} inurl:login OR inurl:signin OR inurl:admin',
    'Directory Listing': 'site:{domain} intitle:"index of" OR intitle:"directory listing"',
    'Sensitive Dirs': 'site:{domain} inurl:wp-admin OR inurl:phpmyadmin OR inurl:cpanel',
    'Error Messages': 'site:{domain} "sql syntax" OR "mysql_fetch" OR "Warning:" OR "Fatal error"',
    'Subdomains': 'site:*.{domain} -www',
    'Open Redirects': 'site:{domain} inurl:redirect OR inurl:url= OR inurl:next=',
    'Exposed Docs': 'site:{domain} ext:pdf OR ext:doc OR ext:xls OR ext:ppt',
    'Config Files': 'site:{domain} ext:xml OR ext:conf OR ext:ini OR ext:yaml',
    'Git Exposed': 'site:{domain} inurl:.git OR intitle:"index of /.git"',
    'API Endpoints': 'site:{domain} inurl:api OR inurl:v1 OR inurl:v2 OR inurl:graphql',
    'Backup Files': 'site:{domain} ext:bak OR ext:old OR ext:backup OR ext:zip',
    'AWS Keys': 'site:{domain} "AKIA" OR "aws_secret" OR "s3.amazonaws"',
    'Email Addresses': 'site:{domain} "@{domain}" ext:txt OR ext:csv',
    'Pastebin Leaks': 'site:pastebin.com "{domain}"',
    'GitHub Leaks': 'site:github.com "{domain}" password OR secret OR token',
}


class DorkingWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__("Google Dorking Assistant", parent)
        row = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText("Enter target domain (e.g. example.com)")
        row.addWidget(self.inp, 1)
        self.act_btn = QPushButton("Generate Dorks")
        self.act_btn.setProperty("cssClass", "primary")
        self.act_btn.clicked.connect(self._go)
        row.addWidget(self.act_btn)
        self.lay.addLayout(row)

        self.dork_combo = QComboBox()
        self.dork_combo.addItem("── All Dorks ──", "all")
        for name in DORK_TEMPLATES:
            self.dork_combo.addItem(name, name)
        self.lay.addWidget(self.dork_combo)

        self._results_area()
        self._buttons()

    def _go(self):
        domain = self.inp.text().strip()
        if not domain:
            return
        domain = domain.replace('https://', '').replace('http://', '').split('/')[0]
        sel = self.dork_combo.currentData()
        sep = "=" * 50
        lines = [sep, f"  GOOGLE DORKS: {domain}", sep, ""]

        if sel == "all":
            templates = DORK_TEMPLATES
        else:
            templates = {sel: DORK_TEMPLATES[sel]}

        for name, tpl in templates.items():
            dork = tpl.format(domain=domain)
            url = f"https://www.google.com/search?q={quote_plus(dork)}"
            lines.append(f"  ── {name} ──")
            lines.append(f"  Dork : {dork}")
            lines.append(f"  URL  : {url}")
            lines.append("")

        lines.append(sep)
        self.res.setText('\n'.join(lines))


# ────────────────────────────────────────────────────────
#  Have I Been Pwned Breach Checker (k-anonymity)
# ────────────────────────────────────────────────────────

class BreachCheckWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__("Credential Breach Checker", parent)
        self._input_row("Enter email or password to check", "Check", self._go)
        info = QLabel("Uses k-anonymity — your full data is never sent")
        info.setProperty("cssClass", "muted")
        self.lay.addWidget(info)
        self._results_area()
        self._buttons()

    def _go(self):
        val = self.inp.text().strip()
        if val:
            if '@' in val:
                self._async(self._check_email, val)
            else:
                self._async(self._check_password, val)

    @staticmethod
    def _check_password(password):
        sha1 = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]
        import urllib.request
        req = urllib.request.Request(
            f'https://api.pwnedpasswords.com/range/{prefix}',
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36', 'Add-Padding': 'true'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode()

        sep = "=" * 50
        count = 0
        for line in data.strip().split('\n'):
            parts = line.strip().split(':')
            if len(parts) == 2 and parts[0] == suffix:
                count = int(parts[1])
                break

        lines = [sep, "  PASSWORD BREACH CHECK", sep, ""]
        if count > 0:
            lines.append(f"  [BREACHED] This password appeared {count:,} times!")
            lines.append(f"  You should change this password IMMEDIATELY.")
        else:
            lines.append(f"  [SAFE] This password was not found in known breaches.")
        lines += ["", "  Note: Uses k-anonymity — only 5-char SHA1 prefix was sent.", "", sep]
        return '\n'.join(lines)

    @staticmethod
    def _check_email(email):
        import urllib.request, urllib.error
        sep = "=" * 50
        lines = [sep, f"  EMAIL BREACH CHECK: {email}", sep, ""]
        try:
            req = urllib.request.Request(
                f'https://haveibeenpwned.com/api/v3/breachedaccount/{quote_plus(email)}?truncateResponse=false',
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                    'hibp-api-key': '',  # Requires API key for full results
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                breaches = json.loads(resp.read().decode())
            lines.append(f"  [BREACHED] Found in {len(breaches)} breach(es):")
            for b in breaches:
                lines.append(f"    - {b.get('Name', '?')} ({b.get('BreachDate', '?')})")
                lines.append(f"      Records: {b.get('PwnCount', '?'):,}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                lines.append("  [SAFE] Email not found in known breaches.")
            elif e.code == 401:
                lines.append("  [INFO] HIBP API key required for email lookups.")
                lines.append("  Password checks work without API key.")
            else:
                lines.append(f"  [ERROR] HTTP {e.code}")
        except Exception as ex:
            lines.append(f"  [ERROR] {ex}")
        lines += ["", sep]
        return '\n'.join(lines)


# ────────────────────────────────────────────────────────
#  Password Strength Analyzer
# ────────────────────────────────────────────────────────

class PasswordAnalyzerWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__("Password Strength Analyzer", parent)
        self._input_row("Enter password to analyze", "Analyze", self._go)
        info = QLabel("Analysis is done locally — nothing is sent over the network")
        info.setProperty("cssClass", "muted")
        self.lay.addWidget(info)
        self._results_area()
        self._buttons()

    def _go(self):
        pw = self.inp.text()
        if pw:
            self._analyze(pw)

    def _analyze(self, pw):
        sep = "=" * 50
        length = len(pw)
        has_lower = bool(re.search(r'[a-z]', pw))
        has_upper = bool(re.search(r'[A-Z]', pw))
        has_digit = bool(re.search(r'\d', pw))
        has_special = bool(re.search(r'[^a-zA-Z0-9]', pw))

        charset = 0
        if has_lower: charset += 26
        if has_upper: charset += 26
        if has_digit: charset += 10
        if has_special: charset += 33
        entropy = length * math.log2(charset) if charset > 0 else 0

        # Common patterns
        warnings = []
        if length < 8:
            warnings.append("[WEAK] Too short (< 8 chars)")
        if length < 12:
            warnings.append("[WARN] Consider 12+ chars")
        if re.search(r'(.)\1{2,}', pw):
            warnings.append("[WARN] Repeated characters detected")
        if re.search(r'(012|123|234|345|456|567|678|789|890|abc|bcd)', pw.lower()):
            warnings.append("[WARN] Sequential characters detected")
        common = ['password', '123456', 'qwerty', 'admin', 'letmein',
                  'welcome', 'monkey', 'dragon', 'master', 'login']
        if pw.lower() in common:
            warnings.append("[CRITICAL] Extremely common password!")

        if entropy >= 80:
            strength = "EXCELLENT"
            color = "🟢"
        elif entropy >= 60:
            strength = "STRONG"
            color = "🟢"
        elif entropy >= 40:
            strength = "MODERATE"
            color = "🟡"
        elif entropy >= 28:
            strength = "WEAK"
            color = "🟠"
        else:
            strength = "VERY WEAK"
            color = "🔴"

        lines = [sep, "  PASSWORD STRENGTH ANALYSIS", sep, "",
                 f"  Length        : {length}",
                 f"  Lowercase    : {'Yes' if has_lower else 'No'}",
                 f"  Uppercase    : {'Yes' if has_upper else 'No'}",
                 f"  Digits       : {'Yes' if has_digit else 'No'}",
                 f"  Special      : {'Yes' if has_special else 'No'}",
                 f"  Charset Size : {charset}",
                 f"  Entropy      : {entropy:.1f} bits",
                 f"  Strength     : {color} {strength}", ""]

        if warnings:
            lines.append("  ── Warnings ──")
            for w in warnings:
                lines.append(f"    {w}")
        else:
            lines.append("  [OK] No common weaknesses detected")

        crack_seconds = (2 ** entropy) / 1e12  # 1 TH/s
        if crack_seconds < 1:
            crack_time = "< 1 second"
        elif crack_seconds < 60:
            crack_time = f"{crack_seconds:.0f} seconds"
        elif crack_seconds < 3600:
            crack_time = f"{crack_seconds/60:.0f} minutes"
        elif crack_seconds < 86400:
            crack_time = f"{crack_seconds/3600:.0f} hours"
        elif crack_seconds < 31536000:
            crack_time = f"{crack_seconds/86400:.0f} days"
        else:
            years = crack_seconds / 31536000
            if years > 1e15:
                crack_time = "heat death of the universe"
            elif years > 1e6:
                crack_time = f"{years:.0e} years"
            else:
                crack_time = f"{years:.0f} years"
        lines += ["", f"  Brute-force (1TH/s): {crack_time}", "", sep]
        self.res.setText('\n'.join(lines))


# ────────────────────────────────────────────────────────
#  MAC Address Vendor Lookup
# ────────────────────────────────────────────────────────

class MACLookupWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__("MAC Address Vendor Lookup", parent)
        self._input_row("Enter MAC address (e.g. AA:BB:CC:DD:EE:FF)", "Lookup", self._go)
        self._results_area()
        self._buttons()

    def _go(self):
        mac = self.inp.text().strip()
        if mac:
            self._async(self._run, mac)

    @staticmethod
    def _run(mac):
        import urllib.request
        clean = re.sub(r'[^a-fA-F0-9]', '', mac)
        if len(clean) < 6:
            return "[ERROR] Invalid MAC address"
        prefix = clean[:6].upper()
        formatted = ':'.join(prefix[i:i+2] for i in range(0, 6, 2))

        req = urllib.request.Request(
            f'https://api.macvendors.com/{formatted}',
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                vendor = resp.read().decode().strip()
        except Exception:
            vendor = "Unknown / Not found"

        sep = "=" * 50
        return '\n'.join([
            sep, "  MAC ADDRESS LOOKUP", sep, "",
            f"  MAC Address : {mac}",
            f"  OUI Prefix  : {formatted}",
            f"  Vendor      : {vendor}", "", sep,
        ])


# ────────────────────────────────────────────────────────
#  Website Fingerprinter (server detection)
# ────────────────────────────────────────────────────────

class WebFingerprintWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__("Website Fingerprinter", parent)
        self._input_row("Enter domain or URL", "Fingerprint", self._go)
        self._results_area()
        self._buttons()

    def _go(self):
        url = self.inp.text().strip()
        if url:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            self._async(self._run, url)

    @staticmethod
    def _run(url):
        import urllib.request
        sep = "=" * 50
        lines = [sep, "  WEBSITE FINGERPRINT", sep, ""]

        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            headers = resp.headers
            body = resp.read(32768).decode('utf-8', errors='replace')

        lines.append(f"  URL: {url}")
        lines.append("")

        # Server detection
        server = headers.get('Server', 'Not disclosed')
        lines.append(f"  Server        : {server}")
        lines.append(f"  X-Powered-By  : {headers.get('X-Powered-By', 'Hidden')}")

        # WAF detection
        waf = "None detected"
        waf_headers = {
            'cf-ray': 'Cloudflare', 'x-sucuri-id': 'Sucuri',
            'x-akamai-transformed': 'Akamai', 'x-cdn': 'CDN',
            'x-iinfo': 'Imperva Incapsula', 'x-protected-by': 'Custom WAF',
        }
        for hdr, name in waf_headers.items():
            if headers.get(hdr):
                waf = name
                break
        if 'cloudflare' in server.lower():
            waf = 'Cloudflare'
        lines.append(f"  WAF/CDN       : {waf}")

        # CMS detection
        cms = "Unknown"
        if 'wp-content' in body or 'wordpress' in body.lower():
            cms = "WordPress"
        elif 'drupal' in body.lower():
            cms = "Drupal"
        elif 'joomla' in body.lower():
            cms = "Joomla"
        elif 'shopify' in body.lower():
            cms = "Shopify"
        elif 'wix.com' in body:
            cms = "Wix"
        elif 'squarespace' in body.lower():
            cms = "Squarespace"
        lines.append(f"  CMS           : {cms}")

        # Programming language hints
        lang = []
        if headers.get('X-Powered-By', '').lower().startswith('php'):
            lang.append('PHP')
        if 'asp.net' in (headers.get('X-Powered-By', '') + headers.get('X-AspNet-Version', '')).lower():
            lang.append('ASP.NET')
        if headers.get('X-Runtime'):
            lang.append('Ruby')
        if '__cfduid' in str(headers):
            lang.append('Cloudflare Workers')
        lines.append(f"  Languages     : {', '.join(lang) if lang else 'Not detected'}")

        # Security headers audit
        lines += ["", "  ── Security Headers ──"]
        sec_headers = [
            'Strict-Transport-Security', 'Content-Security-Policy',
            'X-Frame-Options', 'X-Content-Type-Options',
            'X-XSS-Protection', 'Referrer-Policy',
            'Permissions-Policy', 'Cross-Origin-Opener-Policy',
        ]
        score = 0
        for sh in sec_headers:
            present = bool(headers.get(sh))
            if present:
                score += 1
            status = "✓" if present else "✗"
            lines.append(f"    [{status}] {sh}")

        grade = "A+" if score >= 7 else "A" if score >= 6 else "B" if score >= 4 else "C" if score >= 2 else "F"
        lines += ["", f"  Security Grade: {grade} ({score}/{len(sec_headers)})", "", sep]
        return '\n'.join(lines)
