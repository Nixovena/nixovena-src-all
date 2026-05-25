import os
from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile,
    QWebEngineSettings,
    QWebEngineScript,
    QWebEngineUrlRequestInterceptor,
)

TRACKER_DOMAINS = frozenset({
    'doubleclick.net', 'googlesyndication.com', 'google-analytics.com',
    'googleadservices.com', 'googletagmanager.com', 'adservice.google.com',
    'pagead2.googlesyndication.com', 'connect.facebook.net',
    'pixel.facebook.com', 'analytics.facebook.com', 'ads.twitter.com',
    'static.ads-twitter.com', 'analytics.twitter.com', 'bat.bing.com',
    'ads.linkedin.com', 'snap.licdn.com', 'mc.yandex.ru', 'an.yandex.ru',
    'ad.doubleclick.net', 'stats.wp.com', 'pixel.wp.com', 'hotjar.com',
    'static.hotjar.com', 'mixpanel.com', 'cdn.mxpnl.com',
    'amplitude.com', 'api.amplitude.com', 'segment.io', 'cdn.segment.com',
    'clarity.ms', 'mouseflow.com', 'crazyegg.com',
    'optimizely.com', 'cdn.optimizely.com', 'adnxs.com',
    'taboola.com', 'outbrain.com', 'criteo.com', 'pubmatic.com',
    'rubiconproject.com', 'casalemedia.com', 'openx.net',
    'adsrvr.org', 'scorecardresearch.com', 'quantserve.com',
    'bluekai.com', 'krxd.net', 'exelator.com', 'demdex.net',
    'mathtag.com', 'serving-sys.com', 'eyeota.net', 'contextweb.com',
    'sharethrough.com', 'bidswitch.net', 'smartadserver.com',
    'advertising.com', 'moatads.com', 'turn.com', 'liadm.com',
    'spotxchange.com', 'zedo.com', 'undertone.com', 'media.net',
    'yieldmo.com', 'indexexchange.com', 'rhythmone.com',
    'chartbeat.com', 'chartbeat.net', 'newrelic.com', 'nr-data.net',
    'bugsnag.com', 'sentry.io', 'fullstory.com', 'logrocket.com',
    'inspectlet.com', 'luckyorange.com', 'smartlook.com',
    'heap.io', 'heapanalytics.com', 'kissmetrics.com',
    'branch.io', 'adjust.com', 'appsflyer.com', 'kochava.com',
    'singular.net', 'moengage.com', 'onesignal.com', 'pushwoosh.com',
    'tealium.com', 'tiqcdn.com', 'ensighten.com', 'tagcommander.com',
    'omtrdc.net', '2o7.net', 'adobedtm.com',
    'omniture.com', 'coremetrics.com', 'webtrends.com',
    'adsymptotic.com', 'adroll.com', 'pippio.com', 'pardot.com',
    'mktoresp.com', 'marketo.net', 'hubspot.com', 'hsforms.com',
    'hs-analytics.net', 'intercom.io', 'intercomcdn.com',
    'drift.com', 'driftt.com', 'zendesk.com', 'zdassets.com',
    'freshdesk.com', 'crisp.chat', 'tawk.to', 'livechatinc.com',
    'cookiebot.com', 'cookielaw.org', 'onetrust.com',
    'trustarc.com', 'consensu.org', 'quantcast.com',
    # ── Extended tracker domains ──
    'adsafeprotected.com', 'adtechus.com', 'agkn.com',
    'atdmt.com', 'bizographics.com', 'bounceexchange.com',
    'brealtime.com', 'bttrack.com', 'buysellads.com',
    'cdn.taboola.com', 'clicktale.net',
    'connectad.io', 'convertro.com', 'crwdcntrl.net',
    'data.adsrvr.org',
    'dpm.demdex.net', 'ds.serving-sys.com',
    'everesttech.net', 'fonts.net',
    'go.com', 'hit.gemius.pl', 'ib.adnxs.com',
    'id5-sync.com', 'igodigital.com', 'intellitxt.com',
    'ipredictive.com', 'iterable.com', 'js-agent.newrelic.com',
    'klclick.com', 'kr-labs.com.cn', 'licdn.com',
    'listhub.net', 'liveperson.net', 'lp4.io',
    'ml314.com', 'mookie1.com', 'myvisualiq.net',
    'nativo.com', 'nexac.com', 'nr-data.net',
    'p.adsymptotic.com', 'pardot.com', 'permutive.com',
    'pippio.com', 'postrelease.com', 'pro-market.net',
    'px.ads.linkedin.com', 'qdcount.com',
    'researchgate.net',
    'rlcdn.com', 'rqtrk.eu', 'rubiconproject.com',
    's.pinimg.com', 'scdn.co', 'serving-sys.com',
    'sharethis.com', 'simpli.fi', 'siteimproveanalytics.com',
    'sitescout.com',
    'sp.analytics.yahoo.com', 'stackadapt.com',
    'steelhousemedia.com', 'stickyadstv.com',
    't.co', 'thetradedesk.com', 'tidaltv.com',
    'trackcmp.net', 'tremorhub.com',
    'tribalfusion.com', 'turn.com', 'twimg.com',
    'tynt.com', 'upravel.com', 'weborama.com',
    'widget.intercom.io', 'yandex.ru', 'yimg.com',
    'zenaps.com', 'zqtk.net',
})

KNOWN_FINGERPRINT_ENDPOINTS = frozenset({
    'api.fingerprintjs.com', 'fp.io', 'fpjs.io',
    'arkoselabs.com', 'funcaptcha.com',
    'perfdrive.com', 'betweendigital.com',
    'cdn.jsdelivr.net/npm/@aspect-build/redact',
    'creepjs-api.web.app', 'fpjs.pro',
    'openfpd.com', 'browserleaks.com',
})

SUSPICIOUS_HEADERS_TO_STRIP = [
    b'X-Client-Data',
    b'X-Chrome-Variations',
    b'X-Chrome-Connected',
    b'X-Chrome-ID-Consistency-Request',
    b'Sec-CH-UA-Full-Version-List',
    b'Sec-CH-UA-Bitness',
    b'Sec-CH-UA-Arch',
    b'Sec-CH-UA-Model',
    b'Sec-CH-UA-WoW64',
    b'Sec-CH-Prefers-Color-Scheme',
]


class PrivacyInterceptor(QWebEngineUrlRequestInterceptor):

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self._s = settings_manager
        self._blocked_count = 0
        self._session_blocked = 0

    @property
    def blocked_count(self):
        return self._blocked_count

    @property
    def session_blocked(self):
        return self._session_blocked

    def reset_page_counter(self):
        self._blocked_count = 0

    def interceptRequest(self, info):
        url = info.requestUrl()
        host = url.host().lower()
        url_str = url.toString().lower()
        rtype = info.resourceType()

        # ── DNT / GPC ──
        if self._s.get('do_not_track', True):
            info.setHttpHeader(b'DNT', b'1')
            info.setHttpHeader(b'Sec-GPC', b'1')

        # ── Strip suspicious headers ──
        for hdr in SUSPICIOUS_HEADERS_TO_STRIP:
            info.setHttpHeader(hdr, b'')

        # ── HTTPS Upgrade ──
        if self._s.get('https_only', True):
            if url.scheme() == 'http' and host not in ('localhost', '127.0.0.1', ''):
                upgraded = QUrl(url)
                upgraded.setScheme('https')
                info.redirect(upgraded)
                return

        # ── Tracker & Ad Blocking ──
        if self._s.get('fingerprint_protection', True):
            should_block = False

            # Domain-based blocking
            if self._is_tracker(host) or host in KNOWN_FINGERPRINT_ENDPOINTS:
                should_block = True

            # URL pattern-based ad blocking
            if not should_block:
                ad_patterns = (
                    '/ad/', '/ads/', '/adserver', '/adclick',
                    '/pagead/', '/doubleclick/', '/adview',
                    'track.php', 'pixel.php', 'beacon.',
                    '/collect?', 'analytics.js', '/gtag/',
                    '/ga.js', 'fbevents.js', '/tr?',
                    '/pixel?', 'impression?', '/log?',
                    'telemetry', '/stat?', '/stats.',
                    '_fingerprint', '/fp.js', '/fp?',
                    'clarity.js', 'hotjar.js',
                    'facebook.com/tr', 'quora.com/qevent',
                    'reddit.com/pixel', 'snapchat.com/scevent',
                    'tiktok.com/i18n/pixel',
                )
                for pat in ad_patterns:
                    if pat in url_str:
                        should_block = True
                        break

            # Resource-type: block third-party scripts/images from tracker domains
            if not should_block and rtype in (
                info.ResourceType.ResourceTypeImage,
                info.ResourceType.ResourceTypeMedia,
            ):
                first_host = info.firstPartyUrl().host().lower()
                if first_host and host and host != first_host:
                    fdom = '.'.join(first_host.split('.')[-2:])
                    hdom = '.'.join(host.split('.')[-2:])
                    if fdom != hdom and self._is_tracker(host):
                        should_block = True

            if should_block:
                info.block(True)
                self._blocked_count += 1
                self._session_blocked += 1
                return

        # ── Referrer Policy ──
        policy = self._s.get('referrer_policy', 'strict_origin')
        if policy == 'no_referrer':
            info.setHttpHeader(b'Referer', b'')
        elif policy in ('origin', 'strict_origin'):
            first = info.firstPartyUrl()
            if first.isValid():
                origin = f"{first.scheme()}://{first.host()}"
                info.setHttpHeader(b'Referer', origin.encode())



    @staticmethod
    def _is_tracker(host):
        for domain in TRACKER_DOMAINS:
            if host == domain or host.endswith('.' + domain):
                return True
        return False



CANVAS_FP_JS = r"""
(function() {
    if (window._almightyFpProtected) return;
    window._almightyFpProtected = true;

    // Stable hash seed — deterministic so fingerprint is CONSISTENT not random-unique
    var _seed = 42;
    function stableHash(x) { return (x * 2654435761 >>> 0) & 0xFF; }

    // ── Canvas: deterministic noise so every read gives the same modified output ──
    var origToBlob = HTMLCanvasElement.prototype.toBlob;
    var origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    var origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
    function addCanvasNoise(canvas) {
        try {
            var ctx = canvas.getContext('2d');
            if (!ctx) return;
            var w = canvas.width;
            var h = canvas.height;
            if (w <= 0 || h <= 0 || w > 4096 || h > 4096) return;
            var imgData = ctx.getImageData(0, 0, w, h);
            for (var i = 0; i < imgData.data.length; i += 4) {
                imgData.data[i]   ^= (stableHash(_seed + i) & 1);
                imgData.data[i+1] ^= (stableHash(_seed + i + 1) & 1);
            }
            ctx.putImageData(imgData, 0, 0);
        } catch(e) {}
    }
    HTMLCanvasElement.prototype.toDataURL = function() {
        addCanvasNoise(this);
        return origToDataURL.apply(this, arguments);
    };
    HTMLCanvasElement.prototype.toBlob = function() {
        addCanvasNoise(this);
        return origToBlob.apply(this, arguments);
    };

    // ── WebGL: return most common Intel UHD Graphics values ──
    var VENDOR = 0x9245, RENDERER = 0x9246;
    var fakeExt = {UNMASKED_VENDOR_WEBGL: VENDOR, UNMASKED_RENDERER_WEBGL: RENDERER};
    function patchGL(proto) {
        if (!proto) return;
        var origExt = proto.getExtension;
        var origParam = proto.getParameter;
        proto.getExtension = function(name) {
            if (name === 'WEBGL_debug_renderer_info') return fakeExt;
            return origExt.apply(this, arguments);
        };
        proto.getParameter = function(param) {
            if (param === VENDOR) return 'Google Inc. (Intel)';
            if (param === RENDERER) return 'ANGLE (Intel, Intel(R) UHD Graphics 630, D3D11)';
            if (param === 0x1F01) return 'WebKit';        // GL_RENDERER
            if (param === 0x1F00) return 'WebKit WebGL';  // GL_VENDOR
            try { return origParam.apply(this, arguments); }
            catch(e) { return null; }
        };
    }
    if (typeof WebGLRenderingContext !== 'undefined')
        patchGL(WebGLRenderingContext.prototype);
    if (typeof WebGL2RenderingContext !== 'undefined')
        patchGL(WebGL2RenderingContext.prototype);

    // ── AudioContext: stable tiny offset (not random) ──
    if (typeof AudioBuffer !== 'undefined') {
        var origGCD = AudioBuffer.prototype.getChannelData;
        AudioBuffer.prototype.getChannelData = function() {
            var buf = origGCD.apply(this, arguments);
            if (!buf._patched) {
                for (var i = 0; i < Math.min(buf.length, 5); i++) {
                    buf[i] += 1e-7 * stableHash(_seed + i);
                }
                buf._patched = true;
            }
            return buf;
        };
    }

    // ── Navigator: match Chrome 125 on Windows 10 defaults ──
    var _commonUA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
    var navProps = {
        hardwareConcurrency: 8,
        deviceMemory: 8,
        maxTouchPoints: 0,
        platform: 'Win32',
        vendor: 'Google Inc.',
        userAgent: _commonUA,
        appVersion: '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    };
    for (var key in navProps) {
        try {
            Object.defineProperty(navigator, key, {
                get: (function(v){ return function(){ return v; }; })(navProps[key]),
                configurable: true
            });
        } catch(e) {}
    }
    try {
        Object.defineProperty(navigator, 'language', {
            get: function() { return 'en-US'; }, configurable: true
        });
    } catch(e) {}
    try {
        Object.defineProperty(navigator, 'languages', {
            get: function() { return Object.freeze(['en-US', 'en']); },
            configurable: true
        });
    } catch(e) {}

    // ── User-Agent Client Hints (navigator.userAgentData) ──
    try {
        Object.defineProperty(navigator, 'userAgentData', {
            get: function() {
                return {
                    brands: [
                        {brand: 'Google Chrome', version: '125'},
                        {brand: 'Chromium', version: '125'},
                        {brand: 'Not.A/Brand', version: '24'}
                    ],
                    mobile: false,
                    platform: 'Windows',
                    getHighEntropyValues: function() {
                        return Promise.resolve({
                            architecture: 'x86',
                            bitness: '64',
                            model: '',
                            platformVersion: '15.0.0',
                            fullVersionList: [
                                {brand: 'Google Chrome', version: '125.0.6422.112'},
                                {brand: 'Chromium', version: '125.0.6422.112'}
                            ]
                        });
                    },
                    toJSON: function() {
                        return {brands: this.brands, mobile: false, platform: 'Windows'};
                    }
                };
            }, configurable: true
        });
    } catch(e) {}

    // ── Timezone spoofing: report America/New_York ──
    try {
        var _origDTF = Intl.DateTimeFormat;
        Intl.DateTimeFormat = function() {
            var args = Array.from(arguments);
            if (!args[1]) args[1] = {};
            if (!args[1].timeZone) args[1].timeZone = 'America/New_York';
            return new _origDTF(args[0], args[1]);
        };
        Intl.DateTimeFormat.prototype = _origDTF.prototype;
        Intl.DateTimeFormat.supportedLocalesOf = _origDTF.supportedLocalesOf;
        Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {
            value: function() {
                var opts = _origDTF.prototype.resolvedOptions.call(this);
                opts.timeZone = 'America/New_York';
                return opts;
            }
        });
    } catch(e) {}
    try {
        var _origGetTZO = Date.prototype.getTimezoneOffset;
        Date.prototype.getTimezoneOffset = function() { return 300; };
    } catch(e) {}

    // ── Plugins: mimic standard Chrome PDF plugin set ──
    try {
        var fakeMimeType = {
            type: 'application/pdf',
            suffixes: 'pdf',
            description: 'Portable Document Format',
            enabledPlugin: null
        };
        var fakePlugin = {
            name: 'PDF Viewer',
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format',
            length: 1,
            0: fakeMimeType,
            item: function(i) { return i === 0 ? fakeMimeType : null; },
            namedItem: function(n) { return n === 'application/pdf' ? fakeMimeType : null; }
        };
        fakeMimeType.enabledPlugin = fakePlugin;
        var fakePlugins = {
            length: 5,
            0: fakePlugin,
            1: Object.assign({}, fakePlugin, {name: 'Chrome PDF Viewer'}),
            2: Object.assign({}, fakePlugin, {name: 'Chromium PDF Viewer'}),
            3: Object.assign({}, fakePlugin, {name: 'Microsoft Edge PDF Viewer'}),
            4: Object.assign({}, fakePlugin, {name: 'WebKit built-in PDF'}),
            item: function(i) { return this[i] || null; },
            namedItem: function(n) {
                for (var i = 0; i < 5; i++) { if (this[i] && this[i].name === n) return this[i]; }
                return null;
            },
            refresh: function() {}
        };
        Object.defineProperty(navigator, 'plugins', {
            get: function() { return fakePlugins; }, configurable: true
        });
        Object.defineProperty(navigator, 'mimeTypes', {
            get: function() {
                return { length: 2,
                    0: fakeMimeType,
                    1: Object.assign({}, fakeMimeType, {type: 'text/pdf'}),
                    item: function(i) { return i < 2 ? fakeMimeType : null; },
                    namedItem: function(n) { return n === 'application/pdf' ? fakeMimeType : null; }
                };
            }, configurable: true
        });
    } catch(e) {}

    // ── Screen: 1920x1080 — the most common resolution ──
    var screenProps = {
        width: 1920, height: 1080, availWidth: 1920, availHeight: 1040,
        colorDepth: 24, pixelDepth: 24
    };
    for (var sp in screenProps) {
        try {
            Object.defineProperty(screen, sp, {
                get: (function(v){ return function(){ return v; }; })(screenProps[sp]),
                configurable: true
            });
        } catch(e) {}
    }
    try {
        Object.defineProperty(window, 'devicePixelRatio', {
            get: function(){ return 1; }, configurable: true
        });
        Object.defineProperty(window, 'outerWidth', {
            get: function(){ return 1920; }, configurable: true
        });
        Object.defineProperty(window, 'outerHeight', {
            get: function(){ return 1040; }, configurable: true
        });
        Object.defineProperty(window, 'innerWidth', {
            get: function(){ return 1920; }, configurable: true
        });
        Object.defineProperty(window, 'innerHeight', {
            get: function(){ return 969; }, configurable: true
        });
        Object.defineProperty(window, 'screenX', {
            get: function(){ return 0; }, configurable: true
        });
        Object.defineProperty(window, 'screenY', {
            get: function(){ return 0; }, configurable: true
        });
        Object.defineProperty(window, 'screenLeft', {
            get: function(){ return 0; }, configurable: true
        });
        Object.defineProperty(window, 'screenTop', {
            get: function(){ return 0; }, configurable: true
        });
    } catch(e) {}

    // ── Battery API: return common plugged-in state ──
    if (navigator.getBattery) {
        var fakeBattery = {
            charging: true, chargingTime: 0, dischargingTime: Infinity, level: 1.0,
            addEventListener: function(){}, removeEventListener: function(){},
            dispatchEvent: function(){ return true; },
            onchargingchange: null, onchargingtimechange: null,
            ondischargingtimechange: null, onlevelchange: null
        };
        navigator.getBattery = function() { return Promise.resolve(fakeBattery); };
    }

    // ── Network Information: common 4g values ──
    try {
        if (navigator.connection) {
            var netProps = {effectiveType: '4g', downlink: 10, rtt: 50, saveData: false};
            for (var np in netProps) {
                Object.defineProperty(navigator.connection, np, {
                    get: (function(v){ return function(){ return v; }; })(netProps[np]),
                    configurable: true
                });
            }
        }
    } catch(e) {}

    // ── MediaDevices: return plausible fake devices instead of empty ──
    if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        var fakeDevices = [
            {deviceId: '', groupId: '', kind: 'audioinput', label: ''},
            {deviceId: '', groupId: '', kind: 'videoinput', label: ''},
            {deviceId: '', groupId: '', kind: 'audiooutput', label: ''}
        ];
        navigator.mediaDevices.enumerateDevices = function() {
            return Promise.resolve(fakeDevices);
        };
    }

    // ── Performance.now(): reduce precision to 100μs (matches Chrome default) ──
    var origPerfNow = Performance.prototype.now;
    Performance.prototype.now = function() {
        return Math.round(origPerfNow.call(this) * 10) / 10;
    };

    // ── Speech synthesis: return 0 voices (common before user interaction) ──
    try {
        if (window.speechSynthesis) {
            window.speechSynthesis.getVoices = function() { return []; };
        }
    } catch(e) {}

    // ── Font fingerprint: only allow common web-safe fonts ──
    try {
        if (document.fonts && document.fonts.check) {
            var _origCheck = document.fonts.check.bind(document.fonts);
            var safeList = [
                'serif', 'sans-serif', 'monospace', 'cursive', 'fantasy',
                'Arial', 'Helvetica', 'Times New Roman', 'Times',
                'Courier New', 'Courier', 'Verdana', 'Georgia',
                'Palatino', 'Garamond', 'Trebuchet MS', 'Impact',
                'Comic Sans MS', 'Lucida Console', 'Tahoma',
            ];
            document.fonts.check = function(font) {
                for (var i = 0; i < safeList.length; i++) {
                    if (font.indexOf(safeList[i]) !== -1) return _origCheck(font);
                }
                return false;
            };
        }
    } catch(e) {}

    // ── Keyboard/Gamepad: minimal spoofing ──
    try {
        if (navigator.keyboard && navigator.keyboard.getLayoutMap) {
            navigator.keyboard.getLayoutMap = function() {
                return Promise.reject(new DOMException('Blocked', 'NotAllowedError'));
            };
        }
    } catch(e) {}
    try { navigator.getGamepads = function() { return [null,null,null,null]; }; } catch(e) {}

    // ── Disable Bluetooth/USB/Serial/HID (uncommon APIs) ──
    var blockAPIs = ['bluetooth','usb','serial','hid'];
    blockAPIs.forEach(function(api) {
        try {
            if (navigator[api]) {
                if (navigator[api].requestDevice) {
                    navigator[api].requestDevice = function() {
                        return Promise.reject(new DOMException('Blocked','NotAllowedError'));
                    };
                }
                if (navigator[api].requestPort) {
                    navigator[api].requestPort = function() {
                        return Promise.reject(new DOMException('Blocked','NotAllowedError'));
                    };
                }
                if (navigator[api].getDevices) {
                    navigator[api].getDevices = function() { return Promise.resolve([]); };
                }
                if (navigator[api].getPorts) {
                    navigator[api].getPorts = function() { return Promise.resolve([]); };
                }
            }
        } catch(e) {}
    });

    // ── Sensor APIs: don't delete, just make constructors throw ──
    var sensors = ['Accelerometer','Gyroscope','Magnetometer',
        'AbsoluteOrientationSensor','RelativeOrientationSensor',
        'LinearAccelerationSensor','GravitySensor','AmbientLightSensor'];
    sensors.forEach(function(s) {
        try {
            if (window[s]) {
                window[s] = function() {
                    throw new DOMException('Blocked','NotAllowedError');
                };
            }
        } catch(e) {}
    });

    // ── Date.now precision ──
    var origDateNow = Date.now;
    Date.now = function() { return Math.round(origDateNow() / 10) * 10; };

})();
"""

WEBRTC_BLOCK_JS = r"""
(function() {
    if (window._almightyWebRTCBlocked) return;
    window._almightyWebRTCBlocked = true;

    function BlockedRTC() {
        throw new DOMException('WebRTC disabled for privacy', 'NotAllowedError');
    }
    BlockedRTC.prototype = {};
    BlockedRTC.generateCertificate = function() {
        return Promise.reject(new DOMException('Blocked', 'NotAllowedError'));
    };

    var rtcNames = ['RTCPeerConnection','webkitRTCPeerConnection','mozRTCPeerConnection'];
    rtcNames.forEach(function(n) {
        try {
            Object.defineProperty(window, n, {
                value: BlockedRTC, writable: false, configurable: false
            });
        } catch(e) {}
    });

    try {
        Object.defineProperty(window, 'RTCDataChannel', {
            value: undefined, writable: false, configurable: false
        });
    } catch(e) {}

    if (navigator.mediaDevices) {
        navigator.mediaDevices.getUserMedia = function() {
            return Promise.reject(new DOMException('Blocked', 'NotAllowedError'));
        };
        navigator.mediaDevices.getDisplayMedia = function() {
            return Promise.reject(new DOMException('Blocked', 'NotAllowedError'));
        };
    }
    navigator.getUserMedia = undefined;
    navigator.webkitGetUserMedia = undefined;
    navigator.mozGetUserMedia = undefined;
})();
"""

GEOLOCATION_BLOCK_JS = r"""
(function() {
    if (window._almightyGeoBlocked) return;
    window._almightyGeoBlocked = true;
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition = function(s, e) {
            if (e) { try { e({code: 1, message: 'User denied'}); } catch(x){} }
        };
        navigator.geolocation.watchPosition = function(s, e) {
            if (e) { try { e({code: 1, message: 'User denied'}); } catch(x){} }
            return 0;
        };
        navigator.geolocation.clearWatch = function() {};
    }
})();
"""


class PrivacyProfile:
    @staticmethod
    def create_profile(settings_manager, parent=None, off_the_record=False):
        if off_the_record:
            profile = QWebEngineProfile(parent)
        else:
            profile = QWebEngineProfile("Default", parent)
        PrivacyProfile._configure(profile, settings_manager)
        return profile

    @staticmethod
    def _configure(profile, settings_manager):
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        profile.setHttpCacheMaximumSize(64 * 1024 * 1024)
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
        )
        profile.setSpellCheckEnabled(False)

        # ── Force common UA when fingerprint protection active ──
        if settings_manager.get('fingerprint_protection', True):
            default_ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/125.0.0.0 Safari/537.36")
            profile.setHttpUserAgent(default_ua)
        elif settings_manager.get('user_agent'):
            profile.setHttpUserAgent(settings_manager.get('user_agent'))

        # ── Accept-Language header ──
        profile.setHttpAcceptLanguage('en-US,en;q=0.9')

        # ── Request interceptor ──
        interceptor = PrivacyInterceptor(settings_manager, profile)
        profile.setUrlRequestInterceptor(interceptor)
        profile._privacy_interceptor = interceptor

        # ── Cookie filter ──
        PrivacyProfile._setup_cookie_filter(profile, settings_manager)

        # ── Inject privacy scripts at DocumentCreation time ──
        PrivacyProfile._inject_early_scripts(profile, settings_manager)

    @staticmethod
    def _inject_early_scripts(profile, settings_manager):
        config = {
            'fingerprint_protection': settings_manager.get('fingerprint_protection', True),
            'webrtc_prevention': settings_manager.get('webrtc_prevention', True),
        }
        combined = PrivacyProfile.get_fp_script(config)
        if combined:
            script = QWebEngineScript()
            script.setName("AlmightyPrivacyShield")
            script.setSourceCode(combined)
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            script.setRunsOnSubFrames(True)
            profile.scripts().insert(script)

    @staticmethod
    def _setup_cookie_filter(profile, settings_manager):
        policy = settings_manager.get('cookie_policy', 'block_third_party')

        def cookie_filter(request):
            try:
                if policy == 'block_all':
                    return False
                if policy == 'block_third_party':
                    first = request.firstPartyUrl.host()
                    origin = request.origin.host()
                    if first and origin:
                        fp = '.'.join(first.split('.')[-2:])
                        orig = '.'.join(origin.split('.')[-2:])
                        if fp != orig:
                            return False
                        for td in TRACKER_DOMAINS:
                            if origin == td or origin.endswith('.' + td):
                                return False
            except Exception:
                return False  # Block on error instead of allowing
            return True

        try:
            store = profile.cookieStore()
            store.setCookieFilter(cookie_filter)
            profile._cookie_filter_ref = cookie_filter
        except (AttributeError, TypeError):
            pass

    @staticmethod
    def apply_to_page(settings, config):
        WA = QWebEngineSettings.WebAttribute
        js = config.get('javascript_enabled', True)
        settings.setAttribute(WA.JavascriptEnabled, js)
        settings.setAttribute(WA.JavascriptCanOpenWindows, False)
        settings.setAttribute(WA.JavascriptCanAccessClipboard, False)
        settings.setAttribute(WA.PluginsEnabled, False)
        settings.setAttribute(WA.ScreenCaptureEnabled, False)
        settings.setAttribute(WA.AllowGeolocationOnInsecureOrigins, False)
        settings.setAttribute(WA.WebRTCPublicInterfacesOnly,
                              config.get('webrtc_prevention', True))
        settings.setAttribute(WA.LocalStorageEnabled, True)
        settings.setAttribute(WA.AutoLoadImages, True)
        settings.setAttribute(WA.ScrollAnimatorEnabled, True)
        settings.setAttribute(WA.FullScreenSupportEnabled, True)
        settings.setAttribute(WA.PdfViewerEnabled, True)
        # SECURITY FIX: prevent local file exfiltration
        settings.setAttribute(WA.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(WA.ErrorPageEnabled, True)
        settings.setAttribute(WA.AllowWindowActivationFromJavaScript, False)
        # Disable notification prompts
        try:
            settings.setAttribute(WA.Accelerated2dCanvasEnabled, True)
            settings.setAttribute(WA.WebGLEnabled, True)
        except AttributeError:
            pass
        try:
            settings.setAttribute(WA.PlaybackRequiresUserGesture, True)
        except AttributeError:
            pass

    @staticmethod
    def get_fp_script(config):
        scripts = []
        if config.get('fingerprint_protection', True):
            scripts.append(CANVAS_FP_JS)
        if config.get('webrtc_prevention', True):
            scripts.append(WEBRTC_BLOCK_JS)
        scripts.append(GEOLOCATION_BLOCK_JS)
        return '\n'.join(scripts) if scripts else None

    @staticmethod
    def set_user_agent(profile, ua):
        if ua:
            profile.setHttpUserAgent(ua)

    @staticmethod
    def clear_all_data(profile):
        profile.clearHttpCache()
        profile.clearAllVisitedLinks()
        store = profile.cookieStore()
        if store:
            store.deleteAllCookies()
