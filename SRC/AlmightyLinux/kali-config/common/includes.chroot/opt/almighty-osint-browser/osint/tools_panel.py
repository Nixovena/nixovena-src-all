import hashlib, json, os, socket, ssl, subprocess, base64
from urllib.parse import urlparse, parse_qs

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QTabWidget, QFrame,
    QApplication, QFileDialog, QDialog, QScrollArea, QSpinBox,
    QGroupBox, QSizePolicy,
)
from i18n import tr
from osint.tool_base import ToolWindow, _Worker

# ────────────────────────────────────────────────────────
#  Quick Links
# ────────────────────────────────────────────────────────

OSINT_QUICK_LINKS = [
    ('OSINT Framework',   'https://osintframework.com'),
    ('Shodan',            'https://www.shodan.io'),
    ('IntelligenceX',     'https://intelx.io'),
    ('VirusTotal',        'https://www.virustotal.com'),
    ('Censys',            'https://search.censys.io'),
    ('Have I Been Pwned', 'https://haveibeenpwned.com'),
    ('Wayback Machine',   'https://web.archive.org'),
    ('Hunter.io',         'https://hunter.io'),
    ('crt.sh',            'https://crt.sh'),
    ('SecurityTrails',    'https://securitytrails.com'),
    ('Greynoise',         'https://viz.greynoise.io'),
    ('Dehashed',          'https://dehashed.com'),
    ('Wigle.net',         'https://wigle.net'),
    ('Pulsedive',         'https://pulsedive.com'),
    # ── Extended links ──
    ('URLScan.io',        'https://urlscan.io'),
    ('AlienVault OTX',    'https://otx.alienvault.com'),
    ('ThreatCrowd',       'https://www.threatcrowd.org'),
    ('AbuseIPDB',         'https://www.abuseipdb.com'),
    ('ZoomEye',           'https://www.zoomeye.org'),
    ('FOFA',              'https://en.fofa.info'),
    ('Netcraft',          'https://www.netcraft.com'),
    ('DNSDumpster',       'https://dnsdumpster.com'),
    ('Threatminer',       'https://www.threatminer.org'),
    ('BuiltWith',         'https://builtwith.com'),
    ('Wappalyzer',        'https://www.wappalyzer.com'),
    ('Whatweb',           'https://www.whatweb.net'),
    ('MXToolbox',         'https://mxtoolbox.com'),
    ('ViewDNS.info',      'https://viewdns.info'),
    ('IPinfo.io',         'https://ipinfo.io'),
    ('BGPView',           'https://bgpview.io'),
    ('Robtex',            'https://www.robtex.com'),
    ('PhishTank',         'https://phishtank.org'),
    ('OpenPhish',         'https://openphish.com'),
    ('Hybrid Analysis',   'https://www.hybrid-analysis.com'),
    ('ANY.RUN',           'https://any.run'),
    ('CyberChef',         'https://gchq.github.io/CyberChef'),
]

COMMON_SUBDOMAINS = [
    'www', 'mail', 'ftp', 'admin', 'blog', 'dev', 'staging', 'api',
    'app', 'test', 'portal', 'shop', 'store', 'cdn', 'media', 'img',
    'images', 'static', 'assets', 'files', 'download', 'upload', 'ns1',
    'ns2', 'dns', 'mx', 'smtp', 'pop', 'imap', 'webmail', 'cpanel',
    'whm', 'panel', 'dashboard', 'login', 'auth', 'sso', 'vpn',
    'remote', 'gateway', 'proxy', 'beta', 'alpha', 'demo', 'old',
    'new', 'web', 'www2', 'www3', 'm', 'mobile', 'wap', 'forum',
    'wiki', 'docs', 'help', 'support', 'status', 'monitor', 'git',
    'gitlab', 'jenkins', 'ci', 'cd', 'jira', 'confluence', 'slack',
    'intranet', 'internal', 'staging2', 'uat', 'qa', 'prod', 'backup',
    'db', 'database', 'mysql', 'postgres', 'redis', 'mongo', 'elastic',
    'search', 'cache', 'queue', 'mq', 'rabbitmq', 'kafka', 'grafana',
    'prometheus', 'kibana', 'log', 'logs', 'analytics', 'stats',
    'reports', 'billing', 'pay', 'payments', 'checkout', 'cart',
    'crm', 'erp', 'hr', 'cloud', 'aws', 'azure', 's3',
]

COMMON_PORTS = {
    21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS',
    80: 'HTTP', 110: 'POP3', 111: 'RPCBind', 135: 'MSRPC',
    139: 'NetBIOS', 143: 'IMAP', 161: 'SNMP', 389: 'LDAP',
    443: 'HTTPS', 445: 'SMB', 465: 'SMTPS', 587: 'Submission',
    636: 'LDAPS', 993: 'IMAPS', 995: 'POP3S', 1433: 'MSSQL',
    1521: 'Oracle', 2049: 'NFS', 3306: 'MySQL', 3389: 'RDP',
    5432: 'PostgreSQL', 5900: 'VNC', 6379: 'Redis', 8080: 'HTTP-Proxy',
    8443: 'HTTPS-Alt', 8888: 'HTTP-Alt', 9200: 'Elasticsearch',
    27017: 'MongoDB',
}



# ────────────────────────────────────────────────────────
#  WHOIS
# ────────────────────────────────────────────────────────

class WhoisWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__(tr('whois_lookup'), parent)
        self._input_row(tr('enter_domain'), tr('lookup_btn'), self._go)
        self._results_area()
        self._buttons()

    def _go(self):
        d = self.inp.text().strip()
        if d:
            d = d.replace('https://', '').replace('http://', '')
            d = d.split('/')[0].strip()
            self._async(self._run, d)

    @staticmethod
    def _run(domain):
        try:
            r = subprocess.run(['whois', domain],
                               capture_output=True, text=True, timeout=30)
            output = r.stdout or ''
            if r.stderr:
                output += '\n--- STDERR ---\n' + r.stderr
            if output.strip():
                return output
            return f"No WHOIS data returned for {domain}"
        except FileNotFoundError:
            return "whois not found. Install: sudo apt install whois"
        except subprocess.TimeoutExpired:
            return "Timeout (30s)"
        except Exception as e:
            return f"Error: {e}"


# ────────────────────────────────────────────────────────
#  IP Geolocation
# ────────────────────────────────────────────────────────

class IPLookupWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__(tr('ip_lookup'), parent)
        self._input_row(tr('enter_ip'), tr('lookup_btn'), self._go)
        self._results_area()
        self._buttons()

    def _go(self):
        ip = self.inp.text().strip()
        if ip:
            self._async(self._run, ip)

    @staticmethod
    def _run(ip):
        import urllib.request
        url = (f"http://ip-api.com/json/{ip}?fields=status,message,"
               f"continent,country,countryCode,region,regionName,"
               f"city,zip,lat,lon,timezone,isp,org,as,query")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            d = json.loads(resp.read().decode())
        if d.get('status') == 'fail':
            return f"Failed: {d.get('message')}"
        sep = "=" * 50
        return '\n'.join([
            sep, "  IP GEOLOCATION REPORT", sep, "",
            f"  IP           : {d.get('query')}",
            f"  Continent    : {d.get('continent')}",
            f"  Country      : {d.get('country')} ({d.get('countryCode')})",
            f"  Region       : {d.get('regionName')}",
            f"  City         : {d.get('city')}",
            f"  ZIP          : {d.get('zip')}",
            f"  Lat / Lon    : {d.get('lat')}, {d.get('lon')}",
            f"  Timezone     : {d.get('timezone')}",
            f"  ISP          : {d.get('isp')}",
            f"  Organization : {d.get('org')}",
            f"  AS           : {d.get('as')}", "", sep,
        ])


# ────────────────────────────────────────────────────────
#  DNS Lookup
# ────────────────────────────────────────────────────────

class DNSLookupWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__(tr('dns_lookup'), parent)
        row = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText(tr('enter_domain'))
        self.inp.returnPressed.connect(self._go)
        row.addWidget(self.inp, 1)
        self.rec_combo = QComboBox()
        self.rec_combo.addItems(['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME', 'SOA', 'ANY'])
        self.rec_combo.setFixedWidth(80)
        row.addWidget(self.rec_combo)
        self.act_btn = QPushButton(tr('lookup_btn'))
        self.act_btn.setProperty("cssClass", "primary")
        self.act_btn.clicked.connect(self._go)
        row.addWidget(self.act_btn)
        self.lay.addLayout(row)
        self._results_area()
        self._buttons()

    def _go(self):
        d = self.inp.text().strip()
        if d:
            self._async(self._run, d, self.rec_combo.currentText())

    @staticmethod
    def _run(domain, rtype):
        try:
            r = subprocess.run(
                ['dig', '+noall', '+answer', '+authority', domain, rtype],
                capture_output=True, text=True, timeout=15)
            if r.stdout.strip():
                return f"DNS {domain} ({rtype})\n{'=' * 50}\n\n{r.stdout}"
        except FileNotFoundError:
            pass
        try:
            r2 = subprocess.run(
                ['nslookup', f'-type={rtype}', domain],
                capture_output=True, text=True, timeout=15)
            return f"DNS {domain} ({rtype})\n{'=' * 50}\n\n{r2.stdout}"
        except FileNotFoundError:
            pass
        ips = socket.getaddrinfo(domain, None)
        seen = set()
        lines = [f"DNS {domain}", "=" * 50, ""]
        for info in ips:
            ip = info[4][0]
            fam = 'IPv4' if info[0] == socket.AF_INET else 'IPv6'
            if (ip, fam) not in seen:
                seen.add((ip, fam))
                lines.append(f"  {fam}: {ip}")
        return '\n'.join(lines)


# ────────────────────────────────────────────────────────
#  HTTP Headers
# ────────────────────────────────────────────────────────

class HeadersWindow(ToolWindow):
    SEC_HEADERS = [
        'Strict-Transport-Security', 'Content-Security-Policy',
        'X-Frame-Options', 'X-Content-Type-Options',
        'X-XSS-Protection', 'Referrer-Policy',
        'Permissions-Policy', 'Cross-Origin-Opener-Policy',
        'Cross-Origin-Embedder-Policy', 'Cross-Origin-Resource-Policy',
    ]

    def __init__(self, parent=None):
        super().__init__(tr('http_headers'), parent)
        self._input_row(tr('enter_url_tool'), tr('analyze_btn'), self._go)
        self._results_area()
        self._buttons()

    def _go(self):
        u = self.inp.text().strip()
        if u:
            if not u.startswith(('http://', 'https://')):
                u = 'https://' + u
            self._async(self._run, u)

    @staticmethod
    def _run(url):
        import urllib.request
        req = urllib.request.Request(url, method='HEAD',
                                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.getcode()
            hdrs = resp.headers
        sep = "=" * 50
        lines = [sep, "  HTTP HEADERS ANALYSIS", sep, "",
                 f"  URL         : {url}",
                 f"  Status Code : {code}", "",
                 "  -- Response Headers --", ""]
        for k, v in hdrs.items():
            tag = "[SEC]" if k in HeadersWindow.SEC_HEADERS else "     "
            lines.append(f"  {tag} {k}: {v}")
        lines += ["", "  -- Security Audit --", ""]
        for sh in HeadersWindow.SEC_HEADERS:
            status = "PRESENT" if hdrs.get(sh) else "MISSING"
            lines.append(f"  [{status:7s}] {sh}")
        lines += ["", sep]
        return '\n'.join(lines)


# ────────────────────────────────────────────────────────
#  Hash Calculator
# ────────────────────────────────────────────────────────

class HashWindow(ToolWindow):
    ALGOS = {
        'MD5': hashlib.md5, 'SHA-1': hashlib.sha1,
        'SHA-224': hashlib.sha224, 'SHA-256': hashlib.sha256,
        'SHA-384': hashlib.sha384, 'SHA-512': hashlib.sha512,
        'SHA3-256': hashlib.sha3_256, 'SHA3-512': hashlib.sha3_512,
        'BLAKE2b': hashlib.blake2b, 'BLAKE2s': hashlib.blake2s,
    }

    def __init__(self, parent=None):
        super().__init__(tr('hash_calculator'), parent)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr('hash_type') + ':'))
        self.algo = QComboBox()
        self.algo.addItems(self.ALGOS.keys())
        self.algo.setCurrentText('SHA-256')
        row.addWidget(self.algo, 1)
        self.lay.addLayout(row)
        self.text_in = QTextEdit()
        self.text_in.setPlaceholderText(tr('enter_text'))
        self.text_in.setMaximumHeight(120)
        self.lay.addWidget(self.text_in)
        self.act_btn = QPushButton(tr('calculate_btn'))
        self.act_btn.setProperty("cssClass", "primary")
        self.act_btn.clicked.connect(self._calc)
        self.lay.addWidget(self.act_btn)
        self._results_area()
        self._buttons()

    def _calc(self):
        text = self.text_in.toPlainText()
        if not text:
            return
        name = self.algo.currentText()
        data = text.encode('utf-8')
        h = self.ALGOS[name](data)
        sep = "=" * 50
        self.res.setText('\n'.join([
            sep, "  HASH RESULT", sep, "",
            f"  Algorithm  : {name}",
            f"  Input size : {len(data)} bytes", "",
            f"  Hex    : {h.hexdigest()}", "",
            f"  Base64 : {base64.b64encode(h.digest()).decode()}", "", sep,
        ]))


# ────────────────────────────────────────────────────────
#  SSL Certificate Inspector
# ────────────────────────────────────────────────────────

class SSLCheckWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__(tr('ssl_check'), parent)
        self._input_row(tr('enter_domain'), tr('check_btn'), self._go)
        self._results_area()
        self._buttons()

    def _go(self):
        h = self.inp.text().strip()
        if h:
            self._async(self._run, h)

    @staticmethod
    def _run(host):
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                cert = ss.getpeercert()
                cipher = ss.cipher()
                ver = ss.version()
        sep = "=" * 50
        lines = [sep, "  SSL CERTIFICATE REPORT", sep, "",
                 f"  Host        : {host}",
                 f"  TLS Version : {ver}",
                 f"  Cipher      : {cipher[0] if cipher else 'N/A'}",
                 f"  Bits        : {cipher[2] if cipher else 'N/A'}", ""]
        subj = dict(x[0] for x in cert.get('subject', []))
        lines.append(f"  Common Name : {subj.get('commonName', 'N/A')}")
        issuer = dict(x[0] for x in cert.get('issuer', []))
        lines.append(f"  Issuer      : {issuer.get('organizationName', 'N/A')}")
        lines.append(f"  Issuer CN   : {issuer.get('commonName', 'N/A')}")
        lines.append(f"  Valid From  : {cert.get('notBefore', 'N/A')}")
        lines.append(f"  Valid Until : {cert.get('notAfter', 'N/A')}")
        lines.append(f"  Serial      : {cert.get('serialNumber', 'N/A')}")
        sans = cert.get('subjectAltName', [])
        if sans:
            lines += ["", "  -- Subject Alt Names --"]
            for typ, val in sans:
                lines.append(f"    {typ}: {val}")
        lines += ["", sep]
        return '\n'.join(lines)


# ────────────────────────────────────────────────────────
#  Port Scanner
# ────────────────────────────────────────────────────────

class PortScanWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__(tr('port_scanner'), parent)
        row = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText(tr('enter_domain'))
        row.addWidget(self.inp, 1)
        self.act_btn = QPushButton(tr('analyze_btn'))
        self.act_btn.setProperty("cssClass", "primary")
        self.act_btn.clicked.connect(self._go)
        row.addWidget(self.act_btn)
        self.lay.addLayout(row)
        info = QLabel("Scans top 32 common ports (TCP connect)")
        info.setProperty("cssClass", "muted")
        self.lay.addWidget(info)
        self._results_area()
        self._buttons()

    def _go(self):
        h = self.inp.text().strip()
        if h:
            self._async(self._run, h)

    @staticmethod
    def _run(host):
        sep = "=" * 50
        lines = [sep, f"  PORT SCAN: {host}", sep, ""]
        open_count = 0
        for port, svc in sorted(COMMON_PORTS.items()):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.5)
                result = s.connect_ex((host, port))
                s.close()
                if result == 0:
                    lines.append(f"  [OPEN]   {port:>5d}/tcp  {svc}")
                    open_count += 1
                else:
                    lines.append(f"  [CLOSED] {port:>5d}/tcp  {svc}")
            except Exception as e:
                lines.append(f"  [ERROR]  {port:>5d}/tcp  {svc} - {e}")
        lines += ["", f"  Open ports: {open_count}/{len(COMMON_PORTS)}", "", sep]
        return '\n'.join(lines)


# ────────────────────────────────────────────────────────
#  Subdomain Finder
# ────────────────────────────────────────────────────────

class SubdomainWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__(tr('subdomain_finder'), parent)
        self._input_row(tr('enter_domain'), tr('analyze_btn'), self._go)
        info = QLabel(f"Checks {len(COMMON_SUBDOMAINS)} common subdomain prefixes via DNS")
        info.setProperty("cssClass", "muted")
        self.lay.addWidget(info)
        self._results_area()
        self._buttons()

    def _go(self):
        d = self.inp.text().strip()
        if d:
            self._async(self._run, d)

    @staticmethod
    def _run(domain):
        sep = "=" * 50
        lines = [sep, f"  SUBDOMAIN SCAN: {domain}", sep, ""]
        found = []
        for sub in COMMON_SUBDOMAINS:
            fqdn = f"{sub}.{domain}"
            try:
                addrs = socket.getaddrinfo(fqdn, None, socket.AF_INET)
                ips = list({a[4][0] for a in addrs})
                found.append((fqdn, ips))
                lines.append(f"  [FOUND] {fqdn:40s} -> {', '.join(ips)}")
            except socket.gaierror:
                pass
        lines += ["", f"  Total found: {len(found)}", "", sep]
        return '\n'.join(lines)


# ────────────────────────────────────────────────────────
#  Reverse DNS
# ────────────────────────────────────────────────────────

class ReverseDNSWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__(tr('reverse_dns'), parent)
        self._input_row(tr('enter_ip'), tr('lookup_btn'), self._go)
        self._results_area()
        self._buttons()

    def _go(self):
        ip = self.inp.text().strip()
        if ip:
            self._async(self._run, ip)

    @staticmethod
    def _run(ip):
        sep = "=" * 50
        lines = [sep, "  REVERSE DNS LOOKUP", sep, ""]
        try:
            host, aliases, addrs = socket.gethostbyaddr(ip)
            lines.append(f"  IP        : {ip}")
            lines.append(f"  Hostname  : {host}")
            if aliases:
                lines.append(f"  Aliases   : {', '.join(aliases)}")
            if addrs:
                lines.append(f"  Addresses : {', '.join(addrs)}")
        except socket.herror as e:
            lines.append(f"  No PTR record found for {ip}")
            lines.append(f"  Error: {e}")
        lines += ["", sep]
        return '\n'.join(lines)


# ────────────────────────────────────────────────────────
#  URL Analyzer
# ────────────────────────────────────────────────────────

class URLAnalyzerWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__(tr('url_analyzer'), parent)
        self._input_row(tr('enter_url_tool'), tr('analyze_btn'), self._analyze)
        self.redir_btn = QPushButton(tr('check_redirects'))
        self.redir_btn.clicked.connect(self._redirects)
        self.lay.addWidget(self.redir_btn)
        self._results_area()
        self._buttons()

    def _analyze(self):
        u = self.inp.text().strip()
        if not u:
            return
        if not u.startswith(('http://', 'https://')):
            u = 'https://' + u
        p = urlparse(u)
        params = parse_qs(p.query)
        sep = "=" * 50
        lines = [sep, "  URL ANALYSIS", sep, "",
                 f"  Full URL  : {u}",
                 f"  Scheme    : {p.scheme}",
                 f"  Host      : {p.hostname or 'N/A'}",
                 f"  Port      : {p.port or 'default'}",
                 f"  Path      : {p.path or '/'}",
                 f"  Query     : {p.query or 'None'}",
                 f"  Fragment  : {p.fragment or 'None'}",
                 f"  Username  : {p.username or 'None'}",
                 f"  Password  : {'***' if p.password else 'None'}", ""]
        if params:
            lines.append("  -- Query Parameters --")
            for k, vs in params.items():
                for v in vs:
                    lines.append(f"    {k} = {v}")
            lines.append("")
        lines.append("  -- Safety Analysis --")
        if p.scheme == 'https':
            lines.append("  [OK]   HTTPS encrypted")
        else:
            lines.append("  [WARN] HTTP unencrypted")
        if p.username or p.password:
            lines.append("  [WARN] Credentials in URL")
        if len(u) > 2048:
            lines.append("  [WARN] URL exceeds 2048 chars")
        for pat in ['<script', 'javascript:', 'data:', 'vbscript:']:
            if pat.lower() in u.lower():
                lines.append(f"  [ALERT] Suspicious: {pat}")
        lines += ["", sep]
        self.res.setText('\n'.join(lines))

    def _redirects(self):
        u = self.inp.text().strip()
        if u:
            if not u.startswith(('http://', 'https://')):
                u = 'https://' + u
            self._async(self._trace, u)

    @staticmethod
    def _trace(url):
        import urllib.request, urllib.error
        sep = "=" * 50
        lines = [sep, "  REDIRECT CHAIN", sep, ""]
        cur = url
        for i in range(15):
            try:
                req = urllib.request.Request(cur, method='HEAD',
                                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'})
                resp = urllib.request.build_opener(
                    urllib.request.HTTPRedirectHandler).open(req, timeout=10)
                final = resp.geturl()
                lines.append(f"  {i + 1}. [{resp.getcode()}] {cur}")
                if final == cur:
                    break
                cur = final
            except urllib.error.HTTPError as e:
                lines.append(f"  {i + 1}. [{e.code}] {cur}")
                break
            except Exception as e:
                lines.append(f"  {i + 1}. [ERR] {cur} - {e}")
                break
        lines += ["", sep]
        return '\n'.join(lines)


# ────────────────────────────────────────────────────────
#  Self-IP Check
# ────────────────────────────────────────────────────────

class SelfIPWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__(tr('self_ip'), parent)
        self.act_btn = QPushButton(tr('check_btn'))
        self.act_btn.setProperty("cssClass", "primary")
        self.act_btn.clicked.connect(self._go)
        self.lay.addWidget(self.act_btn)
        self._results_area()
        self._buttons()

    def _go(self):
        self._async(self._run)

    @staticmethod
    def _run():
        import urllib.request
        req = urllib.request.Request('https://api.ipify.org?format=json',
                                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'})
        with urllib.request.urlopen(req, timeout=10) as r:
            ip = json.loads(r.read().decode()).get('ip', '?')
        req2 = urllib.request.Request(
            f'http://ip-api.com/json/{ip}?fields=status,country,countryCode,'
            f'regionName,city,zip,lat,lon,timezone,isp,org,as',
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'})
        with urllib.request.urlopen(req2, timeout=10) as r2:
            g = json.loads(r2.read().decode())
        sep = "=" * 50
        lines = [sep, "  SELF IP CHECK", sep, "",
                 f"  Your IP      : {ip}",
                 f"  Country      : {g.get('country')} ({g.get('countryCode')})",
                 f"  Region       : {g.get('regionName')}",
                 f"  City         : {g.get('city')}",
                 f"  ZIP          : {g.get('zip')}",
                 f"  Lat / Lon    : {g.get('lat')}, {g.get('lon')}",
                 f"  Timezone     : {g.get('timezone')}",
                 f"  ISP          : {g.get('isp')}",
                 f"  Organization : {g.get('org')}",
                 f"  AS           : {g.get('as')}", ""]
        isp_lower = (g.get('isp') or '').lower()
        org_lower = (g.get('org') or '').lower()
        if 'tor' in isp_lower:
            lines.append("  [INFO] Tor network detected")
        elif 'vpn' in isp_lower or 'vpn' in org_lower:
            lines.append("  [INFO] VPN service detected")
        lines += ["", sep]
        return '\n'.join(lines)


# ────────────────────────────────────────────────────────
#  Page Metadata
# ────────────────────────────────────────────────────────

class MetadataWindow(ToolWindow):
    META_JS = """
    (function(){
        var r={};
        r.url=location.href; r.title=document.title||'';
        r.lang=document.documentElement.lang||'';
        var c=document.querySelector('link[rel="canonical"]');
        r.canonical=c?c.href:'';
        var f=document.querySelector('link[rel="icon"],link[rel="shortcut icon"]');
        r.favicon=f?f.href:'';
        var metas=document.querySelectorAll('meta');
        r.meta=[];
        metas.forEach(function(m){
            var e={};
            if(m.name)e.name=m.name;
            if(m.httpEquiv)e.httpEquiv=m.httpEquiv;
            if(m.getAttribute('property'))e.property=m.getAttribute('property');
            if(m.content)e.content=m.content;
            if(m.getAttribute('charset'))e.charset=m.getAttribute('charset');
            if(Object.keys(e).length)r.meta.push(e);
        });
        r.links=document.querySelectorAll('a[href]').length;
        r.images=document.querySelectorAll('img').length;
        r.scripts=document.querySelectorAll('script').length;
        r.styles=document.querySelectorAll('link[rel="stylesheet"]').length;
        r.forms=document.querySelectorAll('form').length;
        r.iframes=document.querySelectorAll('iframe').length;
        r.og={};
        document.querySelectorAll('meta[property^="og:"]').forEach(function(m){
            r.og[m.getAttribute('property')]=m.content;});
        r.tw={};
        document.querySelectorAll('meta[name^="twitter:"]').forEach(function(m){
            r.tw[m.name]=m.content;});
        return JSON.stringify(r);
    })()
    """

    def __init__(self, get_tab, parent=None):
        super().__init__(tr('page_metadata'), parent)
        self._get_tab = get_tab
        self.act_btn = QPushButton(tr('extract_from_page'))
        self.act_btn.setProperty("cssClass", "primary")
        self.act_btn.clicked.connect(self._go)
        self.lay.addWidget(self.act_btn)
        self._results_area()
        self._buttons()

    def _go(self):
        tab = self._get_tab()
        if not tab:
            self.res.setText("No active tab")
            return
        tab.execute_js(self.META_JS, self._on_data)

    def _on_data(self, raw):
        if not raw:
            self.res.setText("Could not extract metadata")
            return
        try:
            d = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            self.res.setText("Parse error")
            return
        sep = "=" * 50
        lines = [sep, "  PAGE METADATA", sep, "",
                 f"  URL        : {d.get('url')}",
                 f"  Title      : {d.get('title')}",
                 f"  Language   : {d.get('lang')}",
                 f"  Canonical  : {d.get('canonical') or 'N/A'}",
                 f"  Favicon    : {d.get('favicon') or 'N/A'}", "",
                 "  -- Statistics --",
                 f"  Links      : {d.get('links', 0)}",
                 f"  Images     : {d.get('images', 0)}",
                 f"  Scripts    : {d.get('scripts', 0)}",
                 f"  Styles     : {d.get('styles', 0)}",
                 f"  Forms      : {d.get('forms', 0)}",
                 f"  Iframes    : {d.get('iframes', 0)}"]
        metas = d.get('meta', [])
        if metas:
            lines += ["", "  -- Meta Tags --"]
            for m in metas:
                parts = [f'{k}="{v}"' for k, v in m.items()]
                lines.append(f"    {' | '.join(parts)}")
        og = d.get('og', {})
        if og:
            lines += ["", "  -- Open Graph --"]
            for k, v in og.items():
                lines.append(f"    {k}: {v}")
        tw = d.get('tw', {})
        if tw:
            lines += ["", "  -- Twitter Card --"]
            for k, v in tw.items():
                lines.append(f"    {k}: {v}")
        lines += ["", sep]
        self.res.setText('\n'.join(lines))


# ────────────────────────────────────────────────────────
#  Technology Detector
# ────────────────────────────────────────────────────────

class TechDetectWindow(ToolWindow):
    DETECT_JS = """
    (function(){
        var t=[];
        if(window.React||document.querySelector('[data-reactroot]'))
            t.push({n:'React',c:'JS Framework'});
        if(window.Vue||document.querySelector('[data-v-]'))
            t.push({n:'Vue.js',c:'JS Framework'});
        if(window.angular||document.querySelector('[ng-app]'))
            t.push({n:'AngularJS',c:'JS Framework'});
        if(window.ng&&window.ng.probe)
            t.push({n:'Angular',c:'JS Framework'});
        if(window.jQuery||window.$)
            t.push({n:'jQuery',c:'JS Library'});
        if(window.__NEXT_DATA__)
            t.push({n:'Next.js',c:'Framework'});
        if(window.__NUXT__)
            t.push({n:'Nuxt.js',c:'Framework'});
        if(window.Gatsby)
            t.push({n:'Gatsby',c:'Framework'});
        if(window.htmx)
            t.push({n:'htmx',c:'JS Library'});
        if(window.Svelte)
            t.push({n:'Svelte',c:'JS Framework'});
        if(document.querySelector('link[href*="bootstrap"]')||
           document.querySelector('.container-fluid'))
            t.push({n:'Bootstrap',c:'CSS'});
        if(document.querySelector('link[href*="tailwind"]'))
            t.push({n:'Tailwind CSS',c:'CSS'});
        if(document.querySelector('meta[name="generator"][content*="WordPress"]')||
           document.querySelector('link[href*="wp-content"]'))
            t.push({n:'WordPress',c:'CMS'});
        if(document.querySelector('meta[name="generator"][content*="Drupal"]'))
            t.push({n:'Drupal',c:'CMS'});
        if(window.Shopify)
            t.push({n:'Shopify',c:'E-Commerce'});
        if(window.ga||window.gtag||
           document.querySelector('script[src*="googletagmanager"]'))
            t.push({n:'Google Analytics',c:'Analytics'});
        if(window.fbq)
            t.push({n:'Facebook Pixel',c:'Analytics'});
        if(window._paq)
            t.push({n:'Matomo',c:'Analytics'});
        var scr=document.querySelectorAll('script[src],link[href]');
        var cdns=new Set();
        scr.forEach(function(s){
            var src=s.src||s.href||'';
            if(src.includes('cloudflare'))cdns.add('Cloudflare');
            if(src.includes('jsdelivr'))cdns.add('jsDelivr');
            if(src.includes('cdnjs'))cdns.add('cdnjs');
            if(src.includes('unpkg'))cdns.add('unpkg');
            if(src.includes('googleapis'))cdns.add('Google APIs');
            if(src.includes('akamai'))cdns.add('Akamai');
        });
        cdns.forEach(function(c){t.push({n:c,c:'CDN'});});
        if(document.querySelector('link[href*="fonts.googleapis"]'))
            t.push({n:'Google Fonts',c:'Fonts'});
        return JSON.stringify(t);
    })()
    """

    def __init__(self, get_tab, parent=None):
        super().__init__(tr('tech_detect'), parent)
        self._get_tab = get_tab
        self.act_btn = QPushButton(tr('detect_tech'))
        self.act_btn.setProperty("cssClass", "primary")
        self.act_btn.clicked.connect(self._go)
        self.lay.addWidget(self.act_btn)
        self._results_area()
        self._buttons()

    def _go(self):
        tab = self._get_tab()
        if not tab:
            self.res.setText("No active tab")
            return
        tab.execute_js(self.DETECT_JS, self._on_data)

    def _on_data(self, raw):
        if not raw:
            self.res.setText("Could not detect")
            return
        try:
            techs = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            self.res.setText("Parse error")
            return
        if not techs:
            self.res.setText("No known technologies detected.")
            return
        cats = {}
        for t in techs:
            cats.setdefault(t.get('c', 'Other'), []).append(t['n'])
        sep = "=" * 50
        lines = [sep, f"  TECHNOLOGY DETECTION ({len(techs)} found)", sep, ""]
        for cat, items in sorted(cats.items()):
            lines.append(f"  -- {cat} --")
            for name in items:
                lines.append(f"    * {name}")
            lines.append("")
        lines.append(sep)
        self.res.setText('\n'.join(lines))


# ────────────────────────────────────────────────────────
#  Notepad
# ────────────────────────────────────────────────────────

class NotepadWindow(QDialog):
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('notepad'))
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.resize(600, 500)
        self._sm = settings_manager
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        self.editor = QTextEdit()
        self.editor.setPlaceholderText(tr('notes_placeholder'))
        self.editor.setFont(QFont("monospace", 12))
        lay.addWidget(self.editor, 1)
        row = QHBoxLayout()
        for label, fn in [(tr('save_notes'), self._save_notes),
                          (tr('export_notes'), self._export),
                          (tr('clear_notes'), self.editor.clear)]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)
        self.status = QLabel("")
        self.status.setProperty("cssClass", "muted")
        lay.addWidget(self.status)
        notes = self._sm.get_notes()
        if notes:
            self.editor.setText(notes)

    def _save_notes(self):
        self._sm.save_notes(self.editor.toPlainText())
        self.status.setText(tr('notes_saved'))

    def _export(self):
        p, _ = QFileDialog.getSaveFileName(self, '', 'osint_notes.txt',
                                           'Text (*.txt);;Markdown (*.md)')
        if p:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            self.status.setText(tr('saved_msg'))

    def closeEvent(self, ev):
        self._save_notes()
        ev.accept()


# ────────────────────────────────────────────────────────
#  Base64 Encoder / Decoder
# ────────────────────────────────────────────────────────

class Base64Window(ToolWindow):
    def __init__(self, parent=None):
        super().__init__("Base64 Encode/Decode", parent)
        self.text_in = QTextEdit()
        self.text_in.setPlaceholderText("Enter text or Base64 string...")
        self.text_in.setMaximumHeight(140)
        self.lay.addWidget(self.text_in)
        row = QHBoxLayout()
        enc = QPushButton("Encode")
        enc.setProperty("cssClass", "primary")
        enc.clicked.connect(self._encode)
        row.addWidget(enc)
        dec = QPushButton("Decode")
        dec.setProperty("cssClass", "primary")
        dec.clicked.connect(self._decode)
        row.addWidget(dec)
        self.lay.addLayout(row)
        self.act_btn = enc
        self._results_area()
        self._buttons()

    def _encode(self):
        t = self.text_in.toPlainText()
        if t:
            encoded = base64.b64encode(t.encode('utf-8')).decode('ascii')
            self.res.setText(f"Base64 Encoded:\n\n{encoded}")

    def _decode(self):
        t = self.text_in.toPlainText().strip()
        if t:
            try:
                decoded = base64.b64decode(t).decode('utf-8', errors='replace')
                self.res.setText(f"Base64 Decoded:\n\n{decoded}")
            except Exception as e:
                self.res.setText(f"[ERROR] Invalid Base64: {e}")


# ────────────────────────────────────────────────────────
#  CIDR / Subnet Calculator
# ────────────────────────────────────────────────────────

class CIDRWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__("CIDR Calculator", parent)
        self._input_row("Enter CIDR (e.g. 192.168.1.0/24)", tr('calculate_btn'), self._go)
        self._results_area()
        self._buttons()

    def _go(self):
        c = self.inp.text().strip()
        if c:
            self._calc(c)

    def _calc(self, cidr):
        import ipaddress
        try:
            net = ipaddress.ip_network(cidr, strict=False)
        except ValueError as e:
            self.res.setText(f"[ERROR] {e}")
            return
        sep = "=" * 50
        hosts = list(net.hosts())
        lines = [sep, "  CIDR CALCULATION", sep, "",
                 f"  Network    : {net.network_address}",
                 f"  Broadcast  : {net.broadcast_address}",
                 f"  Netmask    : {net.netmask}",
                 f"  Hostmask   : {net.hostmask}",
                 f"  Prefix     : /{net.prefixlen}",
                 f"  Total IPs  : {net.num_addresses}",
                 f"  Usable     : {len(hosts)}",
                 f"  Version    : IPv{net.version}",
                 f"  Private    : {net.is_private}",
                 f"  Loopback   : {net.is_loopback}",
                 f"  Multicast  : {net.is_multicast}", ""]
        if len(hosts) <= 256:
            lines.append("  -- Host List --")
            for h in hosts[:256]:
                lines.append(f"    {h}")
        elif len(hosts) > 256:
            lines.append(f"  -- First 10 / Last 10 of {len(hosts)} hosts --")
            for h in hosts[:10]:
                lines.append(f"    {h}")
            lines.append("    ...")
            for h in hosts[-10:]:
                lines.append(f"    {h}")
        lines += ["", sep]
        self.res.setText('\n'.join(lines))


# ────────────────────────────────────────────────────────
#  Email Validator
# ────────────────────────────────────────────────────────

class EmailValidatorWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__("Email Validator", parent)
        self._input_row("Enter email address", tr('check_btn'), self._go)
        self._results_area()
        self._buttons()

    def _go(self):
        e = self.inp.text().strip()
        if e:
            self._async(self._run, e)

    @staticmethod
    def _run(email):
        import re
        sep = "=" * 50
        lines = [sep, "  EMAIL VALIDATION", sep, ""]
        pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
        valid = bool(re.match(pattern, email))
        lines.append(f"  Email      : {email}")
        lines.append(f"  Format     : {'Valid' if valid else 'Invalid'}")
        if valid:
            local, domain = email.rsplit('@', 1)
            lines.append(f"  Local      : {local}")
            lines.append(f"  Domain     : {domain}")
            lines.append("")
            try:
                mx_records = []
                try:
                    r = subprocess.run(['dig', '+short', 'MX', domain],
                                       capture_output=True, text=True, timeout=10)
                    if r.stdout.strip():
                        for line in r.stdout.strip().split('\n'):
                            mx_records.append(line.strip())
                except FileNotFoundError:
                    pass
                if mx_records:
                    lines.append("  -- MX Records --")
                    for mx in mx_records:
                        lines.append(f"    {mx}")
                else:
                    lines.append("  [WARN] No MX records found")
            except Exception:
                pass
            lines.append("")
            try:
                ips = socket.getaddrinfo(domain, None, socket.AF_INET)
                domain_ips = list({a[4][0] for a in ips})
                lines.append("  -- Domain IPs --")
                for ip in domain_ips:
                    lines.append(f"    {ip}")
            except socket.gaierror:
                lines.append("  [WARN] Domain does not resolve")
            disposable = ['tempmail.com', 'throwaway.email', 'guerrillamail.com',
                          'mailinator.com', 'trashmail.com', 'yopmail.com',
                          '10minutemail.com', 'temp-mail.org', 'fakeinbox.com']
            if domain.lower() in disposable:
                lines.append("")
                lines.append("  [ALERT] Disposable email service detected")
        lines += ["", sep]
        return '\n'.join(lines)


# ────────────────────────────────────────────────────────
#  Robots.txt Analyzer
# ────────────────────────────────────────────────────────

class RobotsWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__("Robots.txt Analyzer", parent)
        self._input_row(tr('enter_domain'), tr('analyze_btn'), self._go)
        self._results_area()
        self._buttons()

    def _go(self):
        d = self.inp.text().strip()
        if d:
            if not d.startswith(('http://', 'https://')):
                d = 'https://' + d
            self._async(self._run, d)

    @staticmethod
    def _run(base_url):
        import urllib.request, urllib.error
        sep = "=" * 50
        lines = [sep, "  ROBOTS.TXT ANALYSIS", sep, ""]
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        origin = f"{parsed.scheme}://{parsed.hostname}"
        robots_url = f"{origin}/robots.txt"
        lines.append(f"  URL: {robots_url}")
        lines.append("")
        try:
            req = urllib.request.Request(robots_url,
                                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode('utf-8', errors='replace')
            lines.append(content)
            lines.append("")
            disallowed = [l.split(':', 1)[1].strip()
                          for l in content.split('\n')
                          if l.strip().lower().startswith('disallow:')]
            sitemaps = [l.split(':', 1)[1].strip()
                        for l in content.split('\n')
                        if l.strip().lower().startswith('sitemap:')]
            if disallowed:
                lines += ["", "  -- Disallowed Paths --"]
                for p in disallowed:
                    if p:
                        lines.append(f"    {p}")
            if sitemaps:
                lines += ["", "  -- Sitemaps --"]
                for s in sitemaps:
                    lines.append(f"    {s}")
        except urllib.error.HTTPError as e:
            lines.append(f"  [ERROR] HTTP {e.code}")
        except Exception as e:
            lines.append(f"  [ERROR] {e}")
        lines += ["", sep]
        return '\n'.join(lines)


# ────────────────────────────────────────────────────────
#  Link Extractor (from current page)
# ────────────────────────────────────────────────────────

class LinkExtractorWindow(ToolWindow):
    LINKS_JS = """
    (function(){
        var links = document.querySelectorAll('a[href]');
        var result = [];
        var seen = new Set();
        links.forEach(function(a) {
            var href = a.href;
            var text = (a.textContent || '').trim().substring(0, 60);
            if (href && !seen.has(href)) {
                seen.add(href);
                result.push({url: href, text: text});
            }
        });
        result.sort(function(a,b) { return a.url.localeCompare(b.url); });
        return JSON.stringify(result);
    })()
    """

    def __init__(self, get_tab, parent=None):
        super().__init__("Link Extractor", parent)
        self._get_tab = get_tab
        row = QHBoxLayout()
        self.act_btn = QPushButton("Extract All Links")
        self.act_btn.setProperty("cssClass", "primary")
        self.act_btn.clicked.connect(self._go)
        row.addWidget(self.act_btn)
        self.ext_btn = QPushButton("External Only")
        self.ext_btn.clicked.connect(self._ext)
        row.addWidget(self.ext_btn)
        self.lay.addLayout(row)
        self._results_area()
        self._buttons()
        self._all_links = []

    def _go(self):
        tab = self._get_tab()
        if not tab:
            self.res.setText("No active tab")
            return
        tab.execute_js(self.LINKS_JS, self._on_data)

    def _on_data(self, raw):
        if not raw:
            self.res.setText("No links found")
            return
        try:
            self._all_links = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            self.res.setText("Parse error")
            return
        self._display(self._all_links)

    def _ext(self):
        tab = self._get_tab()
        if not tab:
            return
        host = tab.url().host()
        external = [l for l in self._all_links if host not in l.get('url', '')]
        self._display(external, "EXTERNAL")

    def _display(self, links, label="ALL"):
        sep = "=" * 50
        lines = [sep, f"  LINKS EXTRACTED ({label}: {len(links)})", sep, ""]
        for l in links:
            text = l.get('text', '')
            url = l.get('url', '')
            if text:
                lines.append(f"  [{text}]")
            lines.append(f"    {url}")
            lines.append("")
        lines.append(sep)
        self.res.setText('\n'.join(lines))


# ────────────────────────────────────────────────────────
#  User-Agent Analyzer
# ────────────────────────────────────────────────────────

class UAAnalyzerWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__("User-Agent Analyzer", parent)
        self._input_row("Enter User-Agent string", tr('analyze_btn'), self._go)
        self._results_area()
        self._buttons()

    def _go(self):
        ua = self.inp.text().strip()
        if ua:
            self._analyze(ua)

    def _analyze(self, ua):
        sep = "=" * 50
        lines = [sep, "  USER-AGENT ANALYSIS", sep, "",
                 f"  Raw: {ua}", ""]
        ua_lower = ua.lower()
        browser = "Unknown"
        if 'firefox/' in ua_lower:
            browser = "Firefox"
        elif 'edg/' in ua_lower:
            browser = "Edge"
        elif 'opr/' in ua_lower or 'opera' in ua_lower:
            browser = "Opera"
        elif 'brave' in ua_lower:
            browser = "Brave"
        elif 'vivaldi' in ua_lower:
            browser = "Vivaldi"
        elif 'chrome/' in ua_lower:
            browser = "Chrome"
        elif 'safari/' in ua_lower:
            browser = "Safari"
        elif 'curl/' in ua_lower:
            browser = "cURL"
        elif 'wget/' in ua_lower:
            browser = "Wget"
        elif 'python' in ua_lower:
            browser = "Python"
        elif 'bot' in ua_lower or 'crawler' in ua_lower or 'spider' in ua_lower:
            browser = "Bot/Crawler"
        lines.append(f"  Browser    : {browser}")
        _os = "Unknown"
        if 'windows nt 10' in ua_lower:
            _os = "Windows 10/11"
        elif 'windows nt' in ua_lower:
            _os = "Windows"
        elif 'macintosh' in ua_lower or 'mac os' in ua_lower:
            _os = "macOS"
        elif 'linux' in ua_lower:
            _os = "Linux"
        elif 'android' in ua_lower:
            _os = "Android"
        elif 'iphone' in ua_lower:
            _os = "iOS (iPhone)"
        elif 'ipad' in ua_lower:
            _os = "iOS (iPad)"
        lines.append(f"  OS         : {_os}")
        device = "Desktop"
        if 'mobile' in ua_lower or 'android' in ua_lower or 'iphone' in ua_lower:
            device = "Mobile"
        elif 'tablet' in ua_lower or 'ipad' in ua_lower:
            device = "Tablet"
        elif 'smart-tv' in ua_lower or 'smarttv' in ua_lower:
            device = "Smart TV"
        elif 'playstation' in ua_lower or 'xbox' in ua_lower or 'nintendo' in ua_lower:
            device = "Console"
        elif 'bot' in ua_lower or 'crawler' in ua_lower:
            device = "Bot"
        lines.append(f"  Device     : {device}")
        lines.append("")
        warnings = []
        if 'tor' in ua_lower:
            warnings.append("  [INFO] Tor Browser signature detected")
        if len(ua) > 300:
            warnings.append("  [WARN] Unusually long UA string")
        if 'bot' in ua_lower:
            warnings.append("  [INFO] Bot/crawler identified")
        if not warnings:
            warnings.append("  [OK] No anomalies detected")
        lines += ["  -- Analysis --"] + warnings
        lines += ["", sep]
        self.res.setText('\n'.join(lines))


# ────────────────────────────────────────────────────────
#  Ping / Traceroute
# ────────────────────────────────────────────────────────

class PingWindow(ToolWindow):
    def __init__(self, parent=None):
        super().__init__("Ping / Traceroute", parent)
        row = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText(tr('enter_domain'))
        self.inp.returnPressed.connect(self._ping)
        row.addWidget(self.inp, 1)
        self.act_btn = QPushButton("Ping")
        self.act_btn.setProperty("cssClass", "primary")
        self.act_btn.clicked.connect(self._ping)
        row.addWidget(self.act_btn)
        self.trace_btn = QPushButton("Traceroute")
        self.trace_btn.clicked.connect(self._trace)
        row.addWidget(self.trace_btn)
        self.lay.addLayout(row)
        self._results_area()
        self._buttons()

    def _ping(self):
        h = self.inp.text().strip()
        if h:
            self._async(self._run_ping, h)

    def _trace(self):
        h = self.inp.text().strip()
        if h:
            self._async(self._run_trace, h)

    @staticmethod
    def _run_ping(host):
        try:
            r = subprocess.run(['ping', '-c', '5', '-W', '3', host],
                               capture_output=True, text=True, timeout=30)
            return f"PING {host}\n{'=' * 50}\n\n{r.stdout}"
        except FileNotFoundError:
            return "ping not found"
        except subprocess.TimeoutExpired:
            return "Timeout (30s)"

    @staticmethod
    def _run_trace(host):
        try:
            r = subprocess.run(['traceroute', '-m', '20', '-w', '3', host],
                               capture_output=True, text=True, timeout=60)
            return f"TRACEROUTE {host}\n{'=' * 50}\n\n{r.stdout}"
        except FileNotFoundError:
            try:
                r = subprocess.run(['tracepath', host],
                                   capture_output=True, text=True, timeout=60)
                return f"TRACEPATH {host}\n{'=' * 50}\n\n{r.stdout}"
            except FileNotFoundError:
                return "traceroute/tracepath not found"
        except subprocess.TimeoutExpired:
            return "Timeout (60s)"


# ════════════════════════════════════════════════════════
#  OSINT Sidebar
# ════════════════════════════════════════════════════════

class OSINTSidebar(QWidget):
    open_url = pyqtSignal(str)

    def __init__(self, settings_manager, get_tab_func, parent=None):
        super().__init__(parent)
        self._sm = settings_manager
        self._get_tab = get_tab_func
        self._windows = {}
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(8, 10, 8, 10)
        lay.setSpacing(3)

        def section(title):
            lbl = QLabel(title)
            lbl.setProperty("cssClass", "sidebar-header")
            lay.addWidget(lbl)
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setFrameShadow(QFrame.Shadow.Sunken)
            lay.addWidget(sep)

        def tool_btn(key, cls, *args):
            b = QPushButton(tr(key))
            b.setProperty("cssClass", "sidebar-tool")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda: self._open(key, cls, *args))
            lay.addWidget(b)

        def tool_btn_raw(label, key, cls, *args):
            b = QPushButton(label)
            b.setProperty("cssClass", "sidebar-tool")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda: self._open(key, cls, *args))
            lay.addWidget(b)

        def link_btn(name, url):
            b = QPushButton(name)
            b.setProperty("cssClass", "sidebar-link")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolTip(url)
            b.clicked.connect(lambda: self.open_url.emit(url))
            lay.addWidget(b)

        section("INVESTIGATION")
        tool_btn('whois_lookup', WhoisWindow)
        tool_btn('ip_lookup', IPLookupWindow)
        tool_btn('dns_lookup', DNSLookupWindow)
        tool_btn('reverse_dns', ReverseDNSWindow)
        tool_btn('http_headers', HeadersWindow)
        tool_btn('ssl_check', SSLCheckWindow)
        tool_btn('port_scanner', PortScanWindow)
        tool_btn('subdomain_finder', SubdomainWindow)

        section("RECON")
        tool_btn_raw("Robots.txt Analyzer", 'robots', RobotsWindow)
        tool_btn_raw("Email Validator", 'email_validator', EmailValidatorWindow)
        tool_btn_raw("Ping / Traceroute", 'ping', PingWindow)
        tool_btn_raw("Link Extractor", 'link_extractor', LinkExtractorWindow, 'tab')

        section("ANALYSIS")
        tool_btn('hash_calculator', HashWindow)
        tool_btn('url_analyzer', URLAnalyzerWindow)
        tool_btn('page_metadata', MetadataWindow, 'tab')
        tool_btn('tech_detect', TechDetectWindow, 'tab')

        section("ENCODING")
        tool_btn_raw("Base64 Encode/Decode", 'base64', Base64Window)
        tool_btn_raw("CIDR Calculator", 'cidr', CIDRWindow)
        tool_btn_raw("UA Analyzer", 'ua_analyzer', UAAnalyzerWindow)

        section("UTILITIES")
        tool_btn('self_ip', SelfIPWindow)
        tool_btn('notepad', NotepadWindow, 'settings')

        from osint.osint_tools_extended import (
            SocialSearchWindow, DorkingWindow, BreachCheckWindow,
            PasswordAnalyzerWindow, MACLookupWindow, WebFingerprintWindow,
        )

        section("SOCIAL / HUMINT")
        tool_btn_raw("Username Search", 'social_search', SocialSearchWindow)
        tool_btn_raw("Google Dorking", 'dorking', DorkingWindow)
        tool_btn_raw("Breach Checker", 'breach_check', BreachCheckWindow)

        section("SECURITY")
        tool_btn_raw("Password Analyzer", 'password_analyzer', PasswordAnalyzerWindow)
        tool_btn_raw("MAC Vendor Lookup", 'mac_lookup', MACLookupWindow)
        tool_btn_raw("Website Fingerprint", 'web_fingerprint', WebFingerprintWindow)

        section("QUICK LINKS")
        for name, url in OSINT_QUICK_LINKS:
            link_btn(name, url)

        lay.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _open(self, key, cls, *flags):
        if key in self._windows and self._windows[key].isVisible():
            self._windows[key].activateWindow()
            self._windows[key].raise_()
            return
        if 'tab' in flags:
            win = cls(self._get_tab, self)
        elif 'settings' in flags:
            win = cls(self._sm, self)
        else:
            win = cls(self)
        self._windows[key] = win
        win.show()

    def save_state(self):
        w = self._windows.get('notepad')
        if w and hasattr(w, '_save_notes'):
            w._save_notes()

    def retranslate(self):
        pass

