#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dirent.h>
#include <signal.h>
#include <ctype.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <linux/capability.h>
#include <sys/prctl.h>
#include <time.h>
#include <stdint.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <sched.h>
#include <linux/sched.h>
#include <sys/resource.h>

#define SCAN_INTERVAL_US 200000
#define MAX_PIDS 65536
#define HASH_SIZE 8192
#define KILL_THRESHOLD 70
#define WARN_THRESHOLD 40
#define MAX_FD_CHECK 64
#define MAX_MAPS_LINES 512
#define MAX_PATH_LEN 512
#define MAX_BUF_SIZE 8192
#define FORK_WINDOW_SEC 5
#define FORK_THRESHOLD 50
#define RECHECK_INTERVAL 30
#define CACHE_EXPIRE_SEC 120

typedef struct {
    unsigned long long starttime;
    uint32_t last_check;
    uint16_t threat_score;
    uint8_t check_count;
    uint8_t flags;
} ProcessCache;

#define FLAG_SAFE       0x01
#define FLAG_MONITORED  0x02
#define FLAG_WARNED     0x04

static ProcessCache pid_cache[MAX_PIDS] = {0};

static volatile sig_atomic_t g_running = 1;
static pid_t g_self_pid = 0;

/* Runtime statistics counters */
typedef struct {
    volatile uint64_t namespace_escapes;
    volatile uint64_t fork_bombs_stopped;
    volatile uint64_t miners_killed;
    volatile uint64_t injections_detected;
    volatile uint64_t rootkits_detected;
    volatile uint64_t processes_killed;
    volatile uint64_t scans_completed;
} RuntimeStats;

static RuntimeStats g_stats = {0};

typedef struct {
    uid_t uid;
    int count;
    time_t window_start;
} ForkTracker;

#define MAX_FORK_TRACK 256
static ForkTracker g_fork_track[MAX_FORK_TRACK] = {0};

typedef struct HashEntry {
    const char *key;
    int value;
    struct HashEntry *next;
} HashEntry;

typedef struct {
    HashEntry *buckets[HASH_SIZE];
} HashTable;

static HashTable safe_procs_ht = {0};
static HashTable trusted_parents_ht = {0};
static HashTable restricted_parents_ht = {0};
static HashTable suspicious_children_ht = {0};

static uint32_t hash_string(const char *str) {
    uint32_t hash = 5381;
    int c;
    while ((c = *str++))
        hash = ((hash << 5) + hash) + c;
    return hash % HASH_SIZE;
}

static void ht_insert(HashTable *ht, const char *key, int value) {
    if (!key) return;
    uint32_t idx = hash_string(key);
    /* Check for duplicates to avoid leaking memory on repeated inserts */
    HashEntry *existing = ht->buckets[idx];
    while (existing) {
        if (strcmp(existing->key, key) == 0)
            return; /* Already exists */
        existing = existing->next;
    }
    HashEntry *entry = malloc(sizeof(HashEntry));
    if (!entry) return;
    entry->key = key;
    entry->value = value;
    entry->next = ht->buckets[idx];
    ht->buckets[idx] = entry;
}

static int ht_lookup(HashTable *ht, const char *key) {
    if (!key || key[0] == '\0') return 0;
    uint32_t idx = hash_string(key);
    HashEntry *entry = ht->buckets[idx];
    while (entry) {
        if (strcmp(entry->key, key) == 0)
            return 1;
        entry = entry->next;
    }
    return 0;
}

static void init_hashtable(HashTable *ht, const char **list) {
    for (int i = 0; list[i]; i++) {
        ht_insert(ht, list[i], 1);
    }
}

static void ht_free(HashTable *ht) {
    for (int i = 0; i < HASH_SIZE; i++) {
        HashEntry *entry = ht->buckets[i];
        while (entry) {
            HashEntry *next = entry->next;
            free(entry);
            entry = next;
        }
        ht->buckets[i] = NULL;
    }
}

static const char *DANGEROUS_CMDS[] = {
    "nc -e", "ncat -e", "nc -c", "ncat -c",
    "nc -lvp", "nc -nlvp", "ncat -lvp",
    "nc -lnvp", "nc -vnl",
    
    "/dev/tcp/", "/dev/udp/",
    "bash -i >&", "bash -i >& /dev/tcp",
    "bash -c 'bash -i",
    "0<&196;exec 196<>/dev/tcp",
    "exec 5<>/dev/tcp",
    "/bin/bash -l > /dev/tcp",
    "bash -c 'sh -i",
    
    "python -c 'import socket",
    "python3 -c 'import socket",
    "python -c \"import socket",
    "python3 -c \"import socket",
    "python -c 'import pty",
    "python3 -c 'import pty",
    "python -c 'import os,pty,socket",
    "python3 -c 'import os,pty,socket",
    "__import__('os').dup2",
    "__import__('socket')",
    "socket.socket(socket.AF_INET",
    
    "perl -e 'use Socket",
    "perl -MIO -e",
    "perl -e 'use IO::Socket",
    
    "ruby -rsocket",
    "ruby -e 'require \"socket\"",
    "TCPSocket.new",
    "TCPSocket.open",
    
    "php -r '$sock=fsockopen",
    "php -r \"$sock=fsockopen",
    "fsockopen(",
    "pfsockopen(",
    "stream_socket_client",
    
    "socat exec:",
    "socat tcp:",
    "socat TCP4:",
    "telnet | /bin/sh",
    "telnet | /bin/bash",
    "mknod /tmp/",
    "mkfifo /tmp/",
    
    "base64 -d |", "base64 -d|",
    "base64 --decode |", "base64 --decode|",
    "|base64 -d|", "| base64 -d |",
    "echo|base64 -d", "echo |base64 -d",
    "base64 -d > /tmp/", "base64 -d >/tmp/",
    "base64 -w0",
    
    "base64 -d | bash", "base64 -d | sh",
    "base64 -d|bash", "base64 -d|sh",
    "base64 --decode | bash", "base64 --decode | sh",
    "base64 -d | perl", "base64 -d | python",
    
    "xxd -r", "xxd -p -r",
    "xxd -r |", "xxd -r|",
    "xxd -r -p |",
    
    "gzip -d |", "gunzip |",
    "zcat |", "bzcat |",
    "xzcat |", "lzcat |",
    "gzip -dc |",
    "gunzip -c |",
    
    "openssl enc -d",
    "openssl base64 -d",
    "openssl enc -base64 -d",
    
    "printf '\\x", "printf \"\\x",
    "$'\\x",
    "echo -e '\\x", "echo -e \"\\x",
    "echo -ne '\\x",
    
    "wget -O - |", "wget -O -|",
    "wget -qO- |", "wget -qO-|",
    "wget -O - | bash", "wget -O - | sh",
    "wget -O /tmp/",
    
    "curl |", "curl|",
    "curl -s |", "curl -s|",
    "curl -sL |",
    "curl -o /tmp/",
    "curl -O /tmp/",
    "curl | bash", "curl | sh",
    "curl -s | bash", "curl -s | sh",
    "curl -sSL |",
    "curl -fsSL |",
    
    "capsh --",
    "capsh --gid=0",
    "capsh --uid=0",
    "getcap -r /",
    "setcap cap_",
    "/usr/sbin/getcap",
    
    "vim -c ':!/bin/sh'",
    "vim -c ':shell'",
    "awk 'BEGIN {system",
    "find . -exec /bin/sh",
    "find / -exec /bin/sh",
    "tar -cf /dev/null --checkpoint=1 --checkpoint-action=exec=",
    "zip /tmp/x.zip /etc/passwd -T -TT",
    "python -c 'import os;os.system",
    "python3 -c 'import os;os.system",
    "env /bin/sh -p",
    "expect -c 'spawn /bin/sh",
    "ftp>!/bin/sh",
    "gdb -nx -ex '!sh'",
    "git help config</dev/null",
    "less /etc/passwd!/bin/sh",
    "man man!/bin/sh",
    "more /etc/passwd!/bin/sh",
    "mount -o bind /bin/bash",
    "mysql -e '\\! /bin/sh'",
    "nano -s /bin/sh",
    "sed -n '1e exec sh",
    "ssh -o ProxyCommand=';sh'",
    "strace -o /dev/null /bin/sh",
    "taskset 1 /bin/sh",
    "time /bin/sh",
    "timeout 7d /bin/sh",
    "watch -x sh -c",
    "xargs -a /dev/null sh",
    
    "dd if=/dev/mem", "dd if=/dev/kmem",
    "/proc/self/mem",
    "/proc/kcore",
    "/dev/mem", "/dev/kmem",
    "/dev/port",
    
    "insmod ", "modprobe ",
    "rmmod ",
    "lsmod |",
    "/lib/modules/",
    
    "nsenter -t 1",
    "nsenter --target 1",
    "nsenter -m -u -i -n -p -t",
    "--privileged",
    "docker run --privileged",
    "docker exec --privileged",
    "/var/run/docker.sock",
    "docker.sock",
    "/.dockerenv",
    "mount -t cgroup",
    "cgroup/release_agent",
    "notify_on_release",
    
    "${IFS}",
    "$IFS",
    "{echo,",
    "'b'a's'h",
    "b\"a\"s\"h",
    "/\?\?\?/\?\?\?",
    "/\?\?\?/\?s",
    
    "$(which",
    "`which",
    "$(command",
    "`command",
    
    "eval \"$(", "eval '$(", "eval `",
    "eval $(",
    "exec $(",
    
    "<<< $(",
    "<<<$(", 
    
    "crontab -e",
    "crontab -l",
    "/etc/cron",
    "at -f",
    "systemctl enable",
    "systemctl --user enable",
    "~/.bashrc",
    "~/.profile",
    "~/.bash_profile",
    "/etc/rc.local",
    "/etc/init.d/",
    "update-rc.d",
    
    "/etc/shadow",
    "/etc/passwd && cat /etc/shadow",
    "cat /etc/shadow",
    "unshadow",
    "john ",
    "hashcat",
    "mimipenguin",
    ".ssh/id_rsa",
    ".ssh/authorized_keys",
    "ssh-keygen",
    "cat ~/.ssh/",
    
    "nmap -", "masscan",
    "ping -c 1",
    "/proc/net/",
    "ss -tulpn",
    "netstat -tulpn",
    "arp -a",
    
    /* Additional patterns for modern attacks */
    "powershell",
    "certutil -urlcache",
    "bitsadmin /transfer",
    "mshta http",
    "regsvr32 /s /n /u",
    "rundll32.exe",
    
    NULL
};

static const char *DANGEROUS_ENV[] = {
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "LD_AUDIT",
    "LD_DEBUG",
    "LD_DEBUG_OUTPUT",
    "LD_PROFILE",
    "LD_SHOW_AUXV",
    "LD_USE_LOAD_BIAS",
    "LD_DYNAMIC_WEAK",
    "LD_AOUT_LIBRARY_PATH",
    "LD_AOUT_PRELOAD",
    
    "PYTHONINSPECT",
    "PYTHONSTARTUP",
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTHONCASEOK",
    "PYTHONIOENCODING",
    "PYTHONWARNINGS",
    "PYTHONHASHSEED",
    
    "PERL5OPT",
    "PERL5LIB",
    "PERLLIB",
    "PERL5DB",
    
    "RUBYOPT",
    "RUBYLIB",
    "RUBYPATH",
    "GEM_HOME",
    "GEM_PATH",
    
    "NODE_OPTIONS",
    "NODE_PATH",
    "NODE_REPL_HISTORY",
    
    "LUA_PATH",
    "LUA_CPATH",
    "LUA_INIT",
    
    "PHPRC",
    "PHP_INI_SCAN_DIR",
    
    "JAVA_TOOL_OPTIONS",
    "_JAVA_OPTIONS",
    "JAVA_OPTS",
    "CLASSPATH",
    
    "BASH_ENV",
    "ENV",
    "SHELLOPTS",
    "BASH_FUNC_",
    "CDPATH",
    "GLOBIGNORE",
    "PS4",
    "PROMPT_COMMAND",
    
    "GCONV_PATH",
    "GETCONF_DIR",
    "HOSTALIASES",
    "LOCALDOMAIN",
    "LOCPATH",
    "MALLOC_TRACE",
    "NLSPATH",
    "RESOLV_HOST_CONF",
    "RES_OPTIONS",
    "TMPDIR",
    "TZDIR",
    
    "GTK_MODULES",
    "GTK3_MODULES",
    "GTK_PATH",
    "QT_PLUGIN_PATH",
    "QML_IMPORT_PATH",
    "QML2_IMPORT_PATH",
    "DBUS_SYSTEM_BUS_ADDRESS",
    "DBUS_SESSION_BUS_ADDRESS",
    "XDG_DATA_DIRS",
    
    "SSH_AUTH_SOCK",
    "SSH_AGENT_PID",
    "GPG_AGENT_INFO",
    "GNUPGHOME",
    
    "IFS",
    "PATH=.",
    "PATH=:",
    "http_proxy",
    "https_proxy",
    "ftp_proxy",
    "all_proxy",
    "no_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    
    NULL
};

static const char *TRUSTED_PARENTS[] = {
    "systemd", "init", 
    "apt", "apt-get", "dpkg", "frontend", "aptitude",
    "sudo", "su", "doas", "pkexec", "run0",
    
    /* Display managers */
    "lightdm", "gdm", "gdm3", "sddm", "xdm",
    
    /* GNOME */
    "gnome-shell", "gnome-session", "gnome-terminal-",
    
    /* MATE */
    "mate-session", "mate-panel", "mate-terminal-",
    
    /* KDE/Plasma */
    "kwin_x11", "kwin_wayland", "kded5", "kded6", "plasmashell",
    "konsole",
    
    /* XFCE */
    "xfce4-session", "xfce4-terminal", "xfce4-panel",
    
    /* Terminal emulators — CRITICAL: these spawn bash/sh/zsh as children */
    "alacritty", "kitty", "foot", "wezterm", "tilix",
    "xterm", "urxvt", "rxvt", "st", "sakura",
    "terminator", "guake", "yakuake", "tilda", "terminology",
    "lxterminal", "qterminal", "deepin-terminal",
    "termit", "cool-retro-term", "hyper",
    "tmux", "screen",
    
    /* System services */
    "sshd", "login", "agetty", "getty",
    "cron", "anacron", "atd",
    "systemd-user", "dbus-broker", "dbus-daemon",
    "pipewire", "wireplumber",
    "polkitd",
    
    /* Shells themselves as parents (subshell, script execution) */
    "bash", "sh", "dash", "zsh", "ksh", "fish",
    
    NULL
};

static const char *RESTRICTED_PARENTS[] = {
    "nginx", "apache2", "httpd", "lighttpd", "caddy",
    "gunicorn", "uwsgi", "uvicorn",
    
    "java", "node", "nodejs", "deno", "bun",
    "php-fpm", "php-cgi", "php",
    "ruby", "rails", "puma", "unicorn",
    "python", "python3", "flask", "django",
    "dotnet", "mono",
    
    "mysqld", "mariadbd", "postgres", "postgresql",
    "mongod", "redis-server", "memcached",
    "clickhouse", "influxd",
    
    "rabbitmq-server", "kafka",
    
    "runc", "crun", "containerd-shim",
    
    "postfix", "sendmail", "dovecot", "exim",
    
    NULL
};

static const char *SUSPICIOUS_CHILDREN[] = {
    "sh", "bash", "dash", "zsh", "ksh", "csh", "tcsh", "fish",
    "python", "python2", "python3", "python3.11", "python3.12", "python3.13",
    "perl", "perl5",
    "ruby", "irb",
    "lua", "luajit",
    "php",
    "nc", "netcat", "ncat", "socat",
    "wget", "curl",
    "ssh", "scp", "sftp",
    "telnet", "ftp",
    "nmap", "masscan",
    "base64", "xxd", "od",
    NULL
};

static const char *SAFE_PROCESSES[] = {
    "apt", "apt-get", "dpkg", "frontend", "debconf", "synaptic", 
    "unattended-upgr", "aptitude", "apt-check", "update-notifier",
    "apt-listchanges", "apt-config", "dpkg-deb", "dpkg-query",
    
    "systemd", "systemd-journal", "systemd-logind", "systemd-resolve",
    "systemd-udevd", "systemd-timesyn", "systemd-network", "systemd-oomd",
    "systemd-coredum", "systemd-sleep", "systemd-inhibit", "systemd-tmpfile",
    "init", "kthreadd", "rcu_sched", "ksoftirqd", "kworker", "migration",
    "watchdog", "khungtaskd", "oom_reaper", "writeback", "kcompactd",
    
    "dbus-daemon", "dbus-broker", "dbus-launch", "dbus-monitor",
    
    "NetworkManager", "wpa_supplicant", "avahi-daemon", "dhclient",
    "systemd-resolve", "resolvconf", "dhcpcd", "iwd", "connmand",
    "ModemManager",
    
    "polkitd", "sudo", "su", "gpgv", "gpg-agent", "ssh-agent",
    "gnome-keyring-d", "seahorse", "secret-tool", "pinentry",
    "pam", "pam_unix",
    
    "xz", "gzip", "bzip2", "zstd", "lz4", "pigz", "unzip", "tar", "cpio",
    
    "lightdm", "gdm", "gdm3", "sddm", "xdm", "Xorg", "X",
    "Xwayland", "mutter", "gnome-shell", "weston", "sway",
    "picom", "compton", "xcompmgr",
    
    "pulseaudio", "pipewire", "wireplumber", "pipewire-pulse",
    "pipewire-media-", "alsa", "jackd",
    
    "gnome-shell", "gnome-terminal-", "gnome-session", "gnome-settings-",
    "gnome-control-c", "gnome-software", "gnome-disks", "gnome-system-mo",
    "gnome-text-edit", "gnome-calculato", "gnome-calendar", "gnome-clocks",
    "gnome-contacts", "gnome-maps", "gnome-weather", "gnome-photos",
    "nautilus", "baobab", "evince", "eog", "gedit", "totem",
    "gjs", "gsd-", "gvfsd", "gvfs-", "tracker-miner", "tracker-store",
    "evolution", "evolution-calen", "evolution-addre", "evolution-sourc",
    
    "mate-terminal", "mate-session", "mate-panel", "mate-settings-d",
    "caja", "pluma", "atril", "mate-power-mana", "mate-screensave",
    
    "plasmashell", "kwin_x11", "kwin_wayland", "kded5", "kded6",
    "kglobalaccel5", "kactivitymanag", "ksmserver", "knotify",
    "dolphin", "kate", "konsole", "krunner", "kwalletd",
    "baloo_file", "kscreen_backend", "polkit-kde-auth",
    
    "xfce4-session", "xfwm4", "xfce4-panel", "xfce4-settings-",
    "xfce4-power-man", "xfce4-notifyd", "xfce4-terminal",
    "thunar", "mousepad", "ristretto", "xfdesktop",
    
    "docker", "dockerd", "containerd", "podman",
    "containerd-shim",
    
    "cron", "rsyslogd", "syslogd", "journald",
    "sshd", "login", "agetty", "getty",
    "atd", "anacron", "logrotate",
    "irqbalance", "thermald", "acpid", "upowerd", "upower",
    "accounts-daemon", "rtkit-daemon", "udisksd", "colord",
    
    "firefox", "firefox-esr", "chromium", "chromium-browse", "chrome", "google-chrome",
    "brave", "opera", "msedge", "webkit-", "Isolated Web Co", "Web Content",
    "Socket Process", "Privileged Cont", "RDD Process", "Utility Process",
    "WebExtensions", "GeckoMain", "GPU Process",
    "librewolf", "waterfox", "pale-moon", "falkon",
    
    "thunderbird", "electron", "code", "visual-studio-code", "discord", "spotify",
    "slack", "telegram-deskto", "zoom", "skypeforlinux",
    "flatpak-session", "portal", "xdg-desktop-por",
    "xdg-document-po", "xdg-permission-",
    
    "flatpak", "flatpak-system-", "bwrap",
    "snapd", "snap", "snap-confine",
    
    "alacritty", "kitty", "foot", "wezterm", "tilix",
    "xterm", "urxvt", "st", "sakura", "terminator", "guake", "yakuake",
    
    "vim", "nvim", "nano", "emacs", "micro", "helix",
    "sublime_text", "geany", "atom",
    
    "nemo", "pcmanfm", "spacefm", "ranger", "mc",
    
    "mpv", "vlc", "celluloid", "parole", "rhythmbox", "lollypop",
    "audacious", "clementine",
    
    "feh", "sxiv", "nsxiv", "imv", "gimp", "inkscape",
    
    "okular", "zathura", "mupdf", "libreoffice",
    
    "htop", "btop", "top", "iotop", "dmesg",
    "lsblk", "blkid", "fdisk", "parted", "gparted",
    "nmcli", "nmtui", "iwconfig",
    
    "cupsd", "cups-browsed", "lpd",
    
    "bluetoothd", "blueman-applet", "blueman-manage", "obexd",
    
    "at-spi-bus-laun", "at-spi2-registr", "orca",
    "ibus-daemon", "ibus-x11", "ibus-portal", "fcitx5", "fcitx",
    
    "openvpn", "wireguard", "wg-quick", "openconnect",
    
    "qemu-system-x86", "qemu-system-aa", "libvirtd", "virtqemud",
    "virt-manager", "VBoxSVC", "VBoxXPCOMIPCD",
    "vmtoolsd", "spice-vdagent",
    
    "calamares", "live-config", "live-boot",
    
    "xennytsu",
    "poison",
    "silencer",
    
    NULL
};

static const uint64_t DANGEROUS_CAPS = (
    (1ULL << CAP_SYS_PTRACE) |
    (1ULL << CAP_SYS_ADMIN) |
    (1ULL << CAP_SYS_MODULE) |
    (1ULL << CAP_SYS_RAWIO) |
    (1ULL << CAP_DAC_OVERRIDE) |
    (1ULL << CAP_DAC_READ_SEARCH) |
    (1ULL << CAP_SETUID) |
    (1ULL << CAP_SETGID) |
    (1ULL << CAP_NET_ADMIN) |
    (1ULL << CAP_NET_RAW) |
    (1ULL << CAP_MKNOD) |
    (1ULL << CAP_SYS_CHROOT)
);

static void kill_process(int pid, const char *comm, int score, const char *reason) {
    (void)comm; (void)score; (void)reason;
    if (pid == g_self_pid || pid <= 1) return;
    if (pid >= MAX_PIDS) {
        /* PID out of cache range, still kill but don't touch cache */
        kill(pid, SIGKILL);
        kill(-pid, SIGKILL);
        g_stats.processes_killed++;
        return;
    }
    kill(pid, SIGKILL);
    kill(-pid, SIGKILL);
    memset(&pid_cache[pid], 0, sizeof(ProcessCache));
    g_stats.processes_killed++;
}

static int check_memory_maps(const char *pid_str, char *reason_buf, size_t reason_size) {
    char path[MAX_PATH_LEN];
    char line[1024];
    int score = 0;
    int anon_exec_count = 0;
    int memfd_count = 0;
    int deleted_exec_count = 0;
    
    snprintf(path, sizeof(path), "/proc/%s/maps", pid_str);
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    
    int lines_checked = 0;
    while (fgets(line, sizeof(line), f) && lines_checked < MAX_MAPS_LINES) {
        lines_checked++;
        
        char *perms = strchr(line, ' ');
        if (!perms) continue;
        
        char *dash = strchr(line, '-');
        if (!dash) continue;
        perms = dash;
        while (*perms && !isspace(*perms)) perms++;
        while (*perms && isspace(*perms)) perms++;
        
        if (strlen(perms) < 4) continue;
        if (perms[2] != 'x') continue;
        
        if (strstr(line, "[heap]") || strstr(line, "[stack]")) {
            if (perms[2] == 'x') {
                score += 40;
                anon_exec_count++;
            }
        }
        
        if (strstr(line, "memfd:")) {
            memfd_count++;
            score += 30;
        }
        
        if (strstr(line, "(deleted)") && perms[2] == 'x') {
            deleted_exec_count++;
            score += 15;
        }
        
        /* Detect anonymous RWX mappings (common in shellcode) */
        if (perms[0] == 'r' && perms[1] == 'w' && perms[2] == 'x' && perms[3] == 'p') {
            /* Check if it's truly anonymous (no file backing) */
            char *last_field = strrchr(line, ' ');
            if (last_field && (last_field[1] == '\n' || last_field[1] == '\0' ||
                strcmp(last_field + 1, "\n") == 0)) {
                anon_exec_count++;
                score += 25;
            }
        }
    }
    
    fclose(f);
    
    if (score > 0) {
        snprintf(reason_buf, reason_size, 
                 "Suspicious memory (anon_exec:%d, memfd:%d, deleted:%d)",
                 anon_exec_count, memfd_count, deleted_exec_count);
    }
    
    return score > 60 ? 60 : score;
}

static int check_file_descriptors(const char *pid_str, char *reason_buf, size_t reason_size) {
    char path[MAX_PATH_LEN];
    char link_buf[MAX_PATH_LEN];
    int score = 0;
    
    snprintf(path, sizeof(path), "/proc/%s/fd", pid_str);
    DIR *dir = opendir(path);
    if (!dir) return 0;
    
    struct dirent *ent;
    int fd_count = 0;
    int socket_count = 0;
    int memfd_count = 0;
    
    while ((ent = readdir(dir)) && fd_count < MAX_FD_CHECK) {
        if (ent->d_name[0] == '.') continue;
        fd_count++;
        
        char fd_path[MAX_PATH_LEN * 2];
        snprintf(fd_path, sizeof(fd_path), "%s/%s", path, ent->d_name);
        
        ssize_t len = readlink(fd_path, link_buf, sizeof(link_buf) - 1);
        if (len <= 0) continue;
        link_buf[len] = '\0';
        
        if (strstr(link_buf, "memfd:")) {
            memfd_count++;
        }
        
        if (strncmp(link_buf, "socket:", 7) == 0) {
            socket_count++;
        }
        
        if (strcmp(link_buf, "/dev/mem") == 0 || 
            strcmp(link_buf, "/dev/kmem") == 0 ||
            strcmp(link_buf, "/dev/port") == 0) {
            score += 50;
        }
        
        if (strstr(link_buf, "/proc/") && strstr(link_buf, "/mem")) {
            score += 40;
        }
    }
    
    closedir(dir);
    
    if (socket_count > 10) {
        score += 15;
    }
    
    if (memfd_count > 0) {
        score += memfd_count * 15;
    }
    
    if (score > 0) {
        snprintf(reason_buf, reason_size,
                 "Suspicious FDs (sockets:%d, memfd:%d)",
                 socket_count, memfd_count);
    }
    
    return score > 50 ? 50 : score;
}

static int check_capabilities(const char *pid_str, int is_root, char *reason_buf, size_t reason_size) {
    char path[MAX_PATH_LEN];
    char buf[4096];
    int score = 0;
    
    if (is_root) return 0;
    
    snprintf(path, sizeof(path), "/proc/%s/status", pid_str);
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    
    uint64_t cap_eff = 0;
    
    while (fgets(buf, sizeof(buf), f)) {
        if (strncmp(buf, "CapEff:", 7) == 0) {
            cap_eff = strtoull(buf + 8, NULL, 16);
            break;
        }
    }
    fclose(f);
    
    uint64_t dangerous = cap_eff & DANGEROUS_CAPS;
    if (dangerous) {
        int cap_count = __builtin_popcountll(dangerous);
        score = cap_count * 15;
        
        snprintf(reason_buf, reason_size,
                 "Non-root with dangerous caps (CapEff: 0x%llx)",
                 (unsigned long long)cap_eff);
    }
    
    return score > 45 ? 45 : score;
}

static int check_namespace_escape(const char *pid_str, char *reason_buf, size_t reason_size) {
    char path[MAX_PATH_LEN];
    char link_self[MAX_PATH_LEN], link_target[MAX_PATH_LEN];
    int score = 0;
    const char *ns_types[] = {"mnt", "pid", "net", "uts", "ipc", "user", NULL};

    for (int i = 0; ns_types[i]; i++) {
        snprintf(path, sizeof(path), "/proc/%s/ns/%s", pid_str, ns_types[i]);
        ssize_t len1 = readlink(path, link_self, sizeof(link_self) - 1);
        if (len1 <= 0) continue;
        link_self[len1] = '\0';

        snprintf(path, sizeof(path), "/proc/1/ns/%s", ns_types[i]);
        ssize_t len2 = readlink(path, link_target, sizeof(link_target) - 1);
        if (len2 <= 0) continue;
        link_target[len2] = '\0';

        if (strcmp(link_self, link_target) != 0) {
            char root_link[MAX_PATH_LEN];
            snprintf(path, sizeof(path), "/proc/%s/root", pid_str);
            ssize_t rlen = readlink(path, root_link, sizeof(root_link) - 1);
            if (rlen > 0) {
                root_link[rlen] = '\0';
                if (strcmp(root_link, "/") == 0 && strcmp(ns_types[i], "pid") == 0) {
                    score += 50;
                    g_stats.namespace_escapes++;
                    snprintf(reason_buf, reason_size,
                             "Namespace escape: different %s ns but host root", ns_types[i]);
                }
            }
        }
    }

    snprintf(path, sizeof(path), "/proc/%s/status", pid_str);
    FILE *f = fopen(path, "r");
    if (f) {
        char buf[512];
        int in_userns = 0;
        uint64_t cap_eff = 0;
        while (fgets(buf, sizeof(buf), f)) {
            if (strncmp(buf, "NSpid:", 6) == 0) {
                char *tab2 = strchr(buf + 6, '\t');
                if (tab2) { char *tab3 = strchr(tab2 + 1, '\t'); if (tab3) in_userns = 1; }
            }
            if (strncmp(buf, "CapEff:", 7) == 0)
                cap_eff = strtoull(buf + 8, NULL, 16);
        }
        fclose(f);
        if (in_userns && (cap_eff & (1ULL << CAP_SYS_ADMIN))) {
            score += 35;
            snprintf(reason_buf, reason_size, "CAP_SYS_ADMIN in nested namespace");
        }
    }
    return score > 50 ? 50 : score;
}

static int check_fork_bomb(int pid, int ruid, char *reason_buf, size_t reason_size) {
    (void)pid;
    time_t now = time(NULL);
    int slot = -1;

    for (int i = 0; i < MAX_FORK_TRACK; i++) {
        if (g_fork_track[i].uid == (uid_t)ruid && g_fork_track[i].count > 0) {
            slot = i;
            break;
        }
    }

    if (slot == -1) {
        for (int i = 0; i < MAX_FORK_TRACK; i++) {
            if (g_fork_track[i].count == 0 ||
                (now - g_fork_track[i].window_start) > FORK_WINDOW_SEC) {
                slot = i;
                g_fork_track[i].uid = ruid;
                g_fork_track[i].count = 0;
                g_fork_track[i].window_start = now;
                break;
            }
        }
    }

    if (slot == -1) return 0;

    ForkTracker *ft = &g_fork_track[slot];
    if ((now - ft->window_start) > FORK_WINDOW_SEC) {
        ft->count = 0;
        ft->window_start = now;
    }
    ft->count++;

    if (ft->count > FORK_THRESHOLD) {
        g_stats.fork_bombs_stopped++;
        snprintf(reason_buf, reason_size,
                 "Fork bomb: UID %d spawned %d processes in %ds",
                 ruid, ft->count, FORK_WINDOW_SEC);
        return 80;
    }
    return 0;
}

static int check_cryptominer(const char *pid_str, const char *comm,
                             char *reason_buf, size_t reason_size) {
    int score = 0;
    static const char *miner_names[] = {
        "xmrig", "minerd", "cpuminer", "cgminer", "bfgminer",
        "ethminer", "stratum", "cryptonight", "monero",
        "kswapd0",
        "kdevtmpfsi", "kinsing",
        "xmr-stak", "ccminer", "srbminer",
        "nbminer", "t-rex", "phoenixminer",
        "lolminer", "gminer", "teamredminer",
        NULL
    };
    for (int i = 0; miner_names[i]; i++) {
        if (strcasestr(comm, miner_names[i])) {
            score += 60;
            g_stats.miners_killed++;
            snprintf(reason_buf, reason_size, "Known miner: %s", comm);
            return score;
        }
    }

    char path[MAX_PATH_LEN], buf[MAX_BUF_SIZE];
    snprintf(path, sizeof(path), "/proc/%s/cmdline", pid_str);
    int fd = open(path, O_RDONLY);
    if (fd == -1) return 0;
    ssize_t len = read(fd, buf, sizeof(buf) - 1);
    close(fd);
    if (len <= 0) return 0;
    buf[len] = '\0';
    for (int i = 0; i < len - 1; i++) { if (buf[i] == '\0') buf[i] = ' '; }

    if (strstr(buf, "stratum+tcp://") || strstr(buf, "stratum+ssl://") ||
        strstr(buf, "--coin") || strstr(buf, "--algo=randomx") ||
        strstr(buf, "--donate-level") || strstr(buf, "-o pool.") ||
        strstr(buf, "--cpu-priority") || strstr(buf, "randomx") ||
        strstr(buf, "cryptonight") || strstr(buf, "--algo=kawpow") ||
        strstr(buf, "--algo=ethash") || strstr(buf, "--algo=autolykos")) {
        score += 70;
        g_stats.miners_killed++;
        snprintf(reason_buf, reason_size, "Mining cmdline pattern");
    }
    return score > 70 ? 70 : score;
}

static int check_symlink_attack(const char *pid_str, char *reason_buf, size_t reason_size) {
    char path[MAX_PATH_LEN], link_buf[MAX_PATH_LEN];
    int score = 0;

    snprintf(path, sizeof(path), "/proc/%s/cwd", pid_str);
    ssize_t len = readlink(path, link_buf, sizeof(link_buf) - 1);
    if (len > 0) {
        link_buf[len] = '\0';
        if (strncmp(link_buf, "/proc/", 6) == 0 && strstr(link_buf, "/root")) {
            score += 40;
            snprintf(reason_buf, reason_size, "CWD in /proc root escape path");
        }
    }

    snprintf(path, sizeof(path), "/proc/%s/exe", pid_str);
    len = readlink(path, link_buf, sizeof(link_buf) - 1);
    if (len > 0) {
        link_buf[len] = '\0';
        struct stat st;
        if (stat(link_buf, &st) == 0) {
            if ((st.st_mode & S_ISUID) && (strstr(link_buf, "/tmp/") ||
                strstr(link_buf, "/dev/shm/") || strstr(link_buf, "/var/tmp/"))) {
                score += 60;
                snprintf(reason_buf, reason_size,
                         "SUID binary in writable path: %s", link_buf);
            }
        }
    }
    return score > 60 ? 60 : score;
}

static int check_process_injection(const char *pid_str, char *reason_buf, size_t reason_size) {
    char path[MAX_PATH_LEN], buf[MAX_BUF_SIZE];
    int score = 0;

    snprintf(path, sizeof(path), "/proc/%s/syscall", pid_str);
    int fd = open(path, O_RDONLY);
    if (fd != -1) {
        ssize_t len = read(fd, buf, sizeof(buf) - 1);
        close(fd);
        if (len > 0) {
            buf[len] = '\0';
            long syscall_nr = strtol(buf, NULL, 10);
            /* 101 = ptrace, 311 = process_vm_writev */
            if (syscall_nr == 101 || syscall_nr == 311) {
                score += 45;
                g_stats.injections_detected++;
                snprintf(reason_buf, reason_size,
                         "Possible injection via syscall %ld", syscall_nr);
            }
        }
    }

    snprintf(path, sizeof(path), "/proc/%s/maps", pid_str);
    FILE *f = fopen(path, "r");
    if (f) {
        char line[1024];
        int lines = 0;
        while (fgets(line, sizeof(line), f) && lines < MAX_MAPS_LINES) {
            lines++;
            if (strstr(line, "/dev/shm/") && strstr(line, "r-xp")) {
                score += 40;
                snprintf(reason_buf, reason_size, "Executable mapping from /dev/shm");
                break;
            }
            if (strstr(line, "/tmp/") && strstr(line, "r-xp") && strstr(line, ".so")) {
                score += 35;
                snprintf(reason_buf, reason_size, "Shared library loaded from /tmp");
                break;
            }
        }
        fclose(f);
    }
    return score > 50 ? 50 : score;
}

static int check_hidden_process(const char *pid_str, char *reason_buf, size_t reason_size) {
    int pid = atoi(pid_str);
    int score = 0;
    char path[MAX_PATH_LEN];

    snprintf(path, sizeof(path), "/proc/%s/exe", pid_str);
    char link_buf[MAX_PATH_LEN];
    ssize_t len = readlink(path, link_buf, sizeof(link_buf) - 1);

    if (len > 0) {
        link_buf[len] = '\0';
        if (strstr(link_buf, "/.hidden") || strstr(link_buf, "/...") ||
            strstr(link_buf, "/ ") || strstr(link_buf, "/. ")) {
            score += 60;
            g_stats.rootkits_detected++;
            snprintf(reason_buf, reason_size,
                     "Hidden path executable: %s", link_buf);
        }
    } else {
        snprintf(path, sizeof(path), "/proc/%s/cmdline", pid_str);
        int fd = open(path, O_RDONLY);
        if (fd != -1) {
            char cmd[64];
            ssize_t clen = read(fd, cmd, sizeof(cmd) - 1);
            close(fd);
            if (clen > 0) {
                cmd[clen] = '\0';
                score += 30;
                snprintf(reason_buf, reason_size,
                         "Process with cmdline but no exe (PID %d)", pid);
            }
        }
    }
    return score > 60 ? 60 : score;
}

static int check_kernel_exploit(const char *pid_str, char *reason_buf, size_t reason_size) {
    char path[MAX_PATH_LEN], buf[MAX_BUF_SIZE];
    int score = 0;

    snprintf(path, sizeof(path), "/proc/%s/cmdline", pid_str);
    int fd = open(path, O_RDONLY);
    if (fd == -1) return 0;
    ssize_t len = read(fd, buf, sizeof(buf) - 1);
    close(fd);
    if (len <= 0) return 0;
    buf[len] = '\0';
    for (int i = 0; i < len - 1; i++) { if (buf[i] == '\0') buf[i] = ' '; }

    static const char *exploit_sigs[] = {
        "dirtypipe", "dirty_pipe", "CVE-2022-0847",
        "dirtycow", "dirty_cow", "CVE-2016-5195",
        "CVE-2021-4034", "pwnkit", "pkexec",
        "CVE-2021-3156", "baron_samedit", "sudoedit",
        "CVE-2022-2588", "route4_change",
        "CVE-2023-0386", "overlayfs",
        "CVE-2023-32233", "nftables",
        "CVE-2024-1086", "nf_tables",
        "CVE-2024-0582", "io_uring",
        "CVE-2024-21626", "runc",
        "/proc/self/mem", "splice(", "tee(",
        "userfaultfd", "FUSE_INIT",
        NULL
    };

    for (int i = 0; exploit_sigs[i]; i++) {
        if (strstr(buf, exploit_sigs[i])) {
            score += 75;
            snprintf(reason_buf, reason_size,
                     "Kernel exploit signature: %s", exploit_sigs[i]);
            return score;
        }
    }

    snprintf(path, sizeof(path), "/proc/%s/fd", pid_str);
    DIR *dir = opendir(path);
    if (dir) {
        struct dirent *ent;
        char link[MAX_PATH_LEN];
        int proc_self_writes = 0;
        while ((ent = readdir(dir))) {
            if (ent->d_name[0] == '.') continue;
            char fdpath[MAX_PATH_LEN * 2];
            snprintf(fdpath, sizeof(fdpath), "%s/%s", path, ent->d_name);
            ssize_t llen = readlink(fdpath, link, sizeof(link) - 1);
            if (llen > 0) {
                link[llen] = '\0';
                if (strstr(link, "/proc/self/mem") || strstr(link, "/proc/self/pagemap")) {
                    proc_self_writes++;
                }
            }
        }
        closedir(dir);
        if (proc_self_writes > 0) {
            score += 50;
            snprintf(reason_buf, reason_size,
                     "Process writing to /proc/self/mem (%d FDs)", proc_self_writes);
        }
    }

    return score > 75 ? 75 : score;
}

static int check_cgroup_escape(const char *pid_str, char *reason_buf, size_t reason_size) {
    char path[MAX_PATH_LEN], buf[MAX_BUF_SIZE];
    int score = 0;

    snprintf(path, sizeof(path), "/proc/%s/cgroup", pid_str);
    int fd = open(path, O_RDONLY);
    if (fd == -1) return 0;
    ssize_t len = read(fd, buf, sizeof(buf) - 1);
    close(fd);
    if (len <= 0) return 0;
    buf[len] = '\0';

    if (strstr(buf, "release_agent") || strstr(buf, "notify_on_release")) {
        score += 55;
        snprintf(reason_buf, reason_size, "Cgroup release_agent manipulation");
    }

    snprintf(path, sizeof(path), "/proc/%s/fd", pid_str);
    DIR *dir = opendir(path);
    if (dir) {
        struct dirent *ent;
        char link[MAX_PATH_LEN];
        while ((ent = readdir(dir))) {
            if (ent->d_name[0] == '.') continue;
            char fdpath[MAX_PATH_LEN * 2];
            snprintf(fdpath, sizeof(fdpath), "%s/%s", path, ent->d_name);
            ssize_t llen = readlink(fdpath, link, sizeof(link) - 1);
            if (llen > 0) {
                link[llen] = '\0';
                if (strstr(link, "/sys/fs/cgroup") &&
                    (strstr(link, "release_agent") || strstr(link, "notify_on_release") ||
                     strstr(link, "devices.allow"))) {
                    score += 50;
                    snprintf(reason_buf, reason_size,
                             "Cgroup escape: writing to %s", link);
                    break;
                }
            }
        }
        closedir(dir);
    }

    return score > 55 ? 55 : score;
}

static int check_oom_manipulation(const char *pid_str, char *reason_buf, size_t reason_size) {
    char path[MAX_PATH_LEN], buf[64];
    int score = 0;

    snprintf(path, sizeof(path), "/proc/%s/oom_score_adj", pid_str);
    int fd = open(path, O_RDONLY);
    if (fd == -1) return 0;
    ssize_t len = read(fd, buf, sizeof(buf) - 1);
    close(fd);
    if (len <= 0) return 0;
    buf[len] = '\0';

    int oom_adj = atoi(buf);

    if (oom_adj <= -900) {
        score += 25;
        snprintf(reason_buf, reason_size,
                 "OOM score manipulation: oom_score_adj=%d", oom_adj);
    }

    return score;
}

static int check_network(const char *pid_str, char *reason_buf, size_t reason_size) {
    char path[MAX_PATH_LEN];
    char line[512];
    int score = 0;
    int outbound_count = 0;
    int suspicious_ports = 0;
    
    /* Use /proc/net/tcp instead of /proc/PID/net/tcp for accuracy */
    snprintf(path, sizeof(path), "/proc/%s/net/tcp", pid_str);
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    
    if (!fgets(line, sizeof(line), f)) {
        fclose(f);
        return 0;
    }
    
    while (fgets(line, sizeof(line), f)) {
        unsigned int local_port, remote_port;
        unsigned int local_ip, remote_ip;
        int state;
        
        if (sscanf(line, "%*d: %x:%x %x:%x %x",
                   &local_ip, &local_port, &remote_ip, &remote_port, &state) >= 5) {
            
            if (state == 1 && remote_ip != 0 && remote_ip != 0x0100007F) {
                outbound_count++;
                
                if (local_port == 4444 || local_port == 4445 || 
                    local_port == 1337 || local_port == 31337 ||
                    local_port == 5555 || local_port == 6666 ||
                    local_port == 1234 || local_port == 9001 ||
                    local_port == 6667 || local_port == 6697 ||
                    local_port == 8888 || local_port == 9999 ||
                    remote_port == 4444 || remote_port == 4445 ||
                    remote_port == 1337 || remote_port == 31337 ||
                    remote_port == 5555 || remote_port == 6666 ||
                    remote_port == 1234 || remote_port == 9001) {
                    suspicious_ports++;
                    score += 20;
                }
            }
        }
    }
    fclose(f);
    
    if (suspicious_ports > 0) {
        snprintf(reason_buf, reason_size,
                 "Suspicious network (outbound:%d, sus_ports:%d)",
                 outbound_count, suspicious_ports);
    }
    
    return score > 40 ? 40 : score;
}

static int check_masquerading(const char *pid_str, const char *comm, 
                               char *reason_buf, size_t reason_size) {
    char path[MAX_PATH_LEN];
    char link_buf[MAX_PATH_LEN];
    int score = 0;
    
    snprintf(path, sizeof(path), "/proc/%s/exe", pid_str);
    ssize_t len = readlink(path, link_buf, sizeof(link_buf) - 1);
    
    if (len > 0) {
        link_buf[len] = '\0';
        
        if (comm[0] == '[' && comm[strlen(comm)-1] == ']') {
            /* Verify this is NOT a real kernel thread (kernel threads have no exe) */
            score += 70;
            snprintf(reason_buf, reason_size, "Kernel thread masquerading");
            return score;
        }
        
        if (strstr(link_buf, "memfd:")) {
            score += 45;
            snprintf(reason_buf, reason_size, "Fileless execution (memfd)");
            return score;
        }
        
        if (strstr(link_buf, "/dev/shm/") || 
            (strstr(link_buf, "/tmp/") && strstr(link_buf, ".."))) {
            score += 30;
            snprintf(reason_buf, reason_size, "Execution from temp/shm");
        }
        
        if (strstr(link_buf, "(deleted)")) {
            if (!strstr(link_buf, "/usr/") && !strstr(link_buf, "/lib/") &&
                !strstr(link_buf, "/opt/") && !strstr(link_buf, "/snap/")) {
                score += 25;
                snprintf(reason_buf, reason_size, "Deleted executable");
            }
        }
    }
    
    return score;
}

static int check_cmdline(const char *pid_str, char *reason_buf, size_t reason_size) {
    char path[MAX_PATH_LEN];
    char buf[MAX_BUF_SIZE];
    int score = 0;
    
    snprintf(path, sizeof(path), "/proc/%s/cmdline", pid_str);
    int fd = open(path, O_RDONLY);
    if (fd == -1) return 0;
    
    ssize_t len = read(fd, buf, sizeof(buf) - 1);
    close(fd);
    
    if (len <= 0) return 0;
    buf[len] = '\0';
    
    for (int i = 0; i < len - 1; i++) {
        if (buf[i] == '\0') buf[i] = ' ';
    }
    
    for (int i = 0; DANGEROUS_CMDS[i]; i++) {
        if (strstr(buf, DANGEROUS_CMDS[i])) {
            score += 50;
            snprintf(reason_buf, reason_size, "Dangerous command: %.100s", DANGEROUS_CMDS[i]);
            break;
        }
    }
    
    if (strstr(buf, "echo") && strstr(buf, "base64") && strstr(buf, "|")) {
        score += 35;
        snprintf(reason_buf, reason_size, "Encoded payload execution");
    }
    
    if ((strstr(buf, "bash") || strstr(buf, "sh")) &&
        (strstr(buf, ">&") || strstr(buf, "0<&") || strstr(buf, "0>&"))) {
        score += 40;
        snprintf(reason_buf, reason_size, "Shell with FD redirection");
    }
    
    return score > 50 ? 50 : score;
}

static int check_environ(const char *pid_str, char *reason_buf, size_t reason_size) {
    char path[MAX_PATH_LEN];
    char buf[MAX_BUF_SIZE];
    int score = 0;
    char *found_var = NULL;
    
    snprintf(path, sizeof(path), "/proc/%s/environ", pid_str);
    int fd = open(path, O_RDONLY);
    if (fd == -1) return 0;
    
    ssize_t len = read(fd, buf, sizeof(buf) - 1);
    close(fd);
    
    if (len <= 0) return 0;
    buf[len] = '\0';
    
    size_t pos = 0;
    while (pos < (size_t)len) {
        const char *entry = buf + pos;
        size_t entry_len = strlen(entry);
        
        for (int i = 0; DANGEROUS_ENV[i]; i++) {
            size_t var_len = strlen(DANGEROUS_ENV[i]);
            if (strncmp(entry, DANGEROUS_ENV[i], var_len) == 0 &&
                (entry[var_len] == '=' || entry[var_len] == '\0')) {
                
                if (strcmp(DANGEROUS_ENV[i], "LD_PRELOAD") == 0) {
                    score += 60;
                } else if (strcmp(DANGEROUS_ENV[i], "LD_LIBRARY_PATH") == 0) {
                    score += 30;
                } else if (strcmp(DANGEROUS_ENV[i], "LD_AUDIT") == 0) {
                    score += 55;
                } else {
                    score += 25;
                }
                
                found_var = (char*)DANGEROUS_ENV[i];
            }
        }
        
        pos += entry_len + 1;
    }
    
    if (found_var) {
        snprintf(reason_buf, reason_size, "Dangerous env: %s", found_var);
    }
    
    return score > 60 ? 60 : score;
}

static int check_privesc(int ruid, int euid, int rgid, int egid,
                         int ppid, char *reason_buf, size_t reason_size) {
    int score = 0;
    
    if (ruid != 0 && euid == 0) {
        /* Check if parent is a legitimate privilege escalation mechanism */
        if (ppid > 1) {
            char parent_comm[256] = {0};
            char path[MAX_PATH_LEN];
            snprintf(path, sizeof(path), "/proc/%d/comm", ppid);
            int fd = open(path, O_RDONLY);
            if (fd != -1) {
                ssize_t len = read(fd, parent_comm, sizeof(parent_comm) - 1);
                close(fd);
                if (len > 0) {
                    parent_comm[len] = '\0';
                    char *nl = strchr(parent_comm, '\n');
                    if (nl) *nl = '\0';
                    /* If parent is sudo/su/pkexec/polkitd, this is legitimate */
                    if (strcmp(parent_comm, "sudo") == 0 ||
                        strcmp(parent_comm, "su") == 0 ||
                        strcmp(parent_comm, "pkexec") == 0 ||
                        strcmp(parent_comm, "polkitd") == 0 ||
                        strcmp(parent_comm, "doas") == 0 ||
                        strcmp(parent_comm, "run0") == 0 ||
                        strcmp(parent_comm, "login") == 0 ||
                        strcmp(parent_comm, "sshd") == 0 ||
                        strcmp(parent_comm, "gdm-session-wor") == 0 ||
                        strcmp(parent_comm, "lightdm") == 0 ||
                        strcmp(parent_comm, "sddm-helper") == 0 ||
                        strcmp(parent_comm, "systemd") == 0 ||
                        ht_lookup(&trusted_parents_ht, parent_comm)) {
                        return 0; /* Legitimate privilege escalation */
                    }
                }
            }
        }
        score += 80;
        snprintf(reason_buf, reason_size, 
                 "Privilege escalation (ruid:%d -> euid:0)", ruid);
        return score;
    }
    
    if (rgid != 0 && egid == 0) {
        score += 50;
        snprintf(reason_buf, reason_size,
                 "GID escalation (rgid:%d -> egid:0)", rgid);
    }
    
    return score;
}

static int check_rce_pattern(const char *comm, int ppid,
                             int tty_nr, char *reason_buf, size_t reason_size) {
    int score = 0;
    
    if (ppid <= 1) return 0;
    
    char p_comm[256] = {0};
    char p_path[MAX_PATH_LEN];
    
    snprintf(p_path, sizeof(p_path), "/proc/%d/comm", ppid);
    int fd = open(p_path, O_RDONLY);
    if (fd == -1) return 0;
    
    ssize_t len = read(fd, p_comm, sizeof(p_comm) - 1);
    close(fd);
    
    if (len <= 0) return 0;
    p_comm[len] = '\0';
    if (len > 0 && p_comm[len-1] == '\n') p_comm[len-1] = '\0';
    
    if (ht_lookup(&restricted_parents_ht, p_comm)) {
        if (ht_lookup(&suspicious_children_ht, comm)) {
            score += 70;
            snprintf(reason_buf, reason_size,
                     "RCE pattern: %s spawned %s", p_comm, comm);
            return score;
        }
        
        if (tty_nr > 0) {
            score += 60;
            snprintf(reason_buf, reason_size,
                     "Interactive shell from service %s", p_comm);
            return score;
        }
    }
    
    return score;
}

static int check_tracing(int tracer_pid, char *reason_buf, size_t reason_size) {
    int score = 0;
    
    if (tracer_pid == 0) return 0;
    
    char tracer_comm[256] = {0};
    char path[MAX_PATH_LEN];
    
    snprintf(path, sizeof(path), "/proc/%d/comm", tracer_pid);
    int fd = open(path, O_RDONLY);
    if (fd != -1) {
        ssize_t len = read(fd, tracer_comm, sizeof(tracer_comm) - 1);
        close(fd);
        if (len > 0) {
            tracer_comm[len] = '\0';
            if (len > 0 && tracer_comm[len-1] == '\n') tracer_comm[len-1] = '\0';
        }
    }
    
    if (!ht_lookup(&safe_procs_ht, tracer_comm)) {
        score += 35;
        snprintf(reason_buf, reason_size,
                 "Being traced by PID %d (%s)", tracer_pid, tracer_comm);
    }
    
    return score;
}

static void check_process(const char *pid_str) {
    int pid = atoi(pid_str);
    if (pid <= 1 || pid >= MAX_PIDS) return;
    
    if (pid == g_self_pid) return;
    
    char path[MAX_PATH_LEN];
    char comm[256] = {0};
    char buf[MAX_BUF_SIZE];
    unsigned long long starttime = 0;
    int ppid = 0, tty_nr = 0;
    int ruid = -1, euid = -1, rgid = -1, egid = -1;
    int tracer_pid = 0;
    
    snprintf(path, sizeof(path), "/proc/%s/stat", pid_str);
    int fd = open(path, O_RDONLY);
    if (fd == -1) {
        pid_cache[pid].starttime = 0;
        return;
    }
    
    ssize_t len = read(fd, buf, sizeof(buf) - 1);
    close(fd);
    if (len <= 0) return;
    buf[len] = '\0';
    
    char *p = strrchr(buf, ')');
    if (!p) return;
    p += 2;
    
    int field = 3;
    char *token = p;
    char *next_token;
    
    while (field < 22) {
        next_token = strchr(token, ' ');
        if (!next_token) break;
        *next_token = '\0';
        
        if (field == 4) ppid = atoi(token);
        if (field == 7) tty_nr = atoi(token);
        
        token = next_token + 1;
        field++;
    }
    if (field == 22) starttime = strtoull(token, NULL, 10);
    
    ProcessCache *cache = &pid_cache[pid];
    
    if (cache->starttime == starttime && starttime != 0) {
        if (cache->flags & FLAG_SAFE) {
            return;
        }
    }
    
    snprintf(path, sizeof(path), "/proc/%s/comm", pid_str);
    fd = open(path, O_RDONLY);
    if (fd != -1) {
        len = read(fd, comm, sizeof(comm) - 1);
        if (len > 0) {
            comm[len] = '\0';
            if (len > 0 && comm[len-1] == '\n') comm[len-1] = '\0';
        }
        close(fd);
    }
    
    if (comm[0] == '\0') return;
    
    if (ht_lookup(&safe_procs_ht, comm)) {
        cache->starttime = starttime;
        cache->flags = FLAG_SAFE;
        return;
    }

    for (int i = 0; SAFE_PROCESSES[i]; i++) {
        if (strstr(comm, SAFE_PROCESSES[i])) {
            cache->starttime = starttime;
            cache->flags = FLAG_SAFE;
            return;
        }
    }
    
    if (ppid > 1) {
        char parent_comm[256] = {0};
        snprintf(path, sizeof(path), "/proc/%d/comm", ppid);
        fd = open(path, O_RDONLY);
        if (fd != -1) {
            len = read(fd, parent_comm, sizeof(parent_comm) - 1);
            if (len > 0) {
                parent_comm[len] = '\0';
                if (len > 0 && parent_comm[len-1] == '\n') parent_comm[len-1] = '\0';
            }
            close(fd);
            
            if (ht_lookup(&trusted_parents_ht, parent_comm)) {
                cache->starttime = starttime;
                cache->flags = FLAG_SAFE;
                return;
            }
        }
    }
    
    snprintf(path, sizeof(path), "/proc/%s/status", pid_str);
    FILE *f = fopen(path, "r");
    if (f) {
        while (fgets(buf, sizeof(buf), f)) {
            if (strncmp(buf, "Uid:", 4) == 0) {
                sscanf(buf, "Uid:\t%d\t%d", &ruid, &euid);
            } else if (strncmp(buf, "Gid:", 4) == 0) {
                sscanf(buf, "Gid:\t%d\t%d", &rgid, &egid);
            } else if (strncmp(buf, "TracerPid:", 10) == 0) {
                sscanf(buf, "TracerPid:\t%d", &tracer_pid);
            }
        }
        fclose(f);
    }
    
    /* Skip root processes for most checks (but not all) */
    if (ruid == 0 && euid == 0) {
        /* Root processes: only check for known malware names and cryptominers */
        char temp_reason[256] = {0};
        int score = check_cryptominer(pid_str, comm, temp_reason, sizeof(temp_reason));
        if (score >= KILL_THRESHOLD) {
            kill_process(pid, comm, score, temp_reason);
            return;
        }
        score = check_masquerading(pid_str, comm, temp_reason, sizeof(temp_reason));
        if (score >= KILL_THRESHOLD) {
            kill_process(pid, comm, score, temp_reason);
            return;
        }
        cache->starttime = starttime;
        cache->flags = FLAG_SAFE;
        return;
    }
    
    int total_score = 0;
    char reason[512] = {0};
    char temp_reason[256] = {0};
    int reason_len = 0;
    
    int score = check_privesc(ruid, euid, rgid, egid, ppid, temp_reason, sizeof(temp_reason));
    if (score > 0) {
        total_score += score;
        reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len, 
                               "%s; ", temp_reason);
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
        return;
    }
    
    score = check_rce_pattern(comm, ppid, tty_nr, temp_reason, sizeof(temp_reason));
    if (score > 0) {
        total_score += score;
        reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                               "%s; ", temp_reason);
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
        return;
    }
    
    score = check_masquerading(pid_str, comm, temp_reason, sizeof(temp_reason));
    if (score > 0) {
        total_score += score;
        reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                               "%s; ", temp_reason);
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
        return;
    }
    
    int do_expensive_checks = (cache->starttime != starttime) || (total_score > 0);
    
    if (do_expensive_checks && ruid != 0) {
        score = check_cmdline(pid_str, temp_reason, sizeof(temp_reason));
        if (score > 0) {
            total_score += score;
            reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                                   "%s; ", temp_reason);
        }
        
        score = check_environ(pid_str, temp_reason, sizeof(temp_reason));
        if (score > 0) {
            total_score += score;
            reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                                   "%s; ", temp_reason);
        }
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
        return;
    }
    
    if (do_expensive_checks) {
        score = check_memory_maps(pid_str, temp_reason, sizeof(temp_reason));
        if (score > 0) {
            total_score += score;
            reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                                   "%s; ", temp_reason);
        }
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
        return;
    }
    
    if (ruid != 0) {
        score = check_capabilities(pid_str, ruid == 0, temp_reason, sizeof(temp_reason));
        if (score > 0) {
            total_score += score;
            reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                                   "%s; ", temp_reason);
        }
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
        return;
    }
    
    if (do_expensive_checks && total_score > 20) {
        score = check_file_descriptors(pid_str, temp_reason, sizeof(temp_reason));
        if (score > 0) {
            total_score += score;
            reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                                   "%s; ", temp_reason);
        }
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
        return;
    }
    
    if (tracer_pid != 0) {
        score = check_tracing(tracer_pid, temp_reason, sizeof(temp_reason));
        if (score > 0) {
            total_score += score;
            reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                                   "%s; ", temp_reason);
        }
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
        return;
    }
    
    if (total_score > 30) {
        score = check_network(pid_str, temp_reason, sizeof(temp_reason));
        if (score > 0) {
            total_score += score;
            reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                                   "%s; ", temp_reason);
        }
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
        return;
    }
    
    if (do_expensive_checks) {
        score = check_namespace_escape(pid_str, temp_reason, sizeof(temp_reason));
        if (score > 0) {
            total_score += score;
            reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                                   "%s; ", temp_reason);
        }
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
        return;
    }
    
    if (ruid > 0) {
        score = check_fork_bomb(pid, ruid, temp_reason, sizeof(temp_reason));
        if (score > 0) {
            total_score += score;
            reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                                   "%s; ", temp_reason);
        }
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
        return;
    }
    
    score = check_cryptominer(pid_str, comm, temp_reason, sizeof(temp_reason));
    if (score > 0) {
        total_score += score;
        reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                               "%s; ", temp_reason);
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
        return;
    }
    
    if (do_expensive_checks && ruid != 0) {
        score = check_symlink_attack(pid_str, temp_reason, sizeof(temp_reason));
        if (score > 0) {
            total_score += score;
            reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                                   "%s; ", temp_reason);
        }
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
        return;
    }
    
    if (do_expensive_checks && total_score > 10) {
        score = check_process_injection(pid_str, temp_reason, sizeof(temp_reason));
        if (score > 0) {
            total_score += score;
            reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                                   "%s; ", temp_reason);
        }
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
        return;
    }
    
    if (do_expensive_checks) {
        score = check_hidden_process(pid_str, temp_reason, sizeof(temp_reason));
        if (score > 0) {
            total_score += score;
            reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                                   "%s; ", temp_reason);
        }
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
        return;
    }
    
    if (do_expensive_checks) {
        score = check_kernel_exploit(pid_str, temp_reason, sizeof(temp_reason));
        if (score > 0) {
            total_score += score;
            reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                                   "%s; ", temp_reason);
        }
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
        return;
    }
    
    if (do_expensive_checks) {
        score = check_cgroup_escape(pid_str, temp_reason, sizeof(temp_reason));
        if (score > 0) {
            total_score += score;
            reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                                   "%s; ", temp_reason);
        }
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
        return;
    }
    
    if (ruid != 0) {
        score = check_oom_manipulation(pid_str, temp_reason, sizeof(temp_reason));
        if (score > 0) {
            total_score += score;
            reason_len += snprintf(reason + reason_len, sizeof(reason) - reason_len,
                                   "%s; ", temp_reason);
        }
    }
    
    if (total_score >= KILL_THRESHOLD) {
        kill_process(pid, comm, total_score, reason);
    } else if (total_score >= WARN_THRESHOLD) {
        cache->flags |= (FLAG_WARNED | FLAG_MONITORED);
    }
    
    cache->starttime = starttime;
    cache->threat_score = total_score;
    cache->check_count++;
    
    if (total_score == 0 && do_expensive_checks) {
        cache->flags = FLAG_SAFE;
    }
}

static void init_hashtables(void) {
    init_hashtable(&safe_procs_ht, SAFE_PROCESSES);
    init_hashtable(&trusted_parents_ht, TRUSTED_PARENTS);
    init_hashtable(&restricted_parents_ht, RESTRICTED_PARENTS);
    init_hashtable(&suspicious_children_ht, SUSPICIOUS_CHILDREN);
}

static void cleanup_hashtables(void) {
    ht_free(&safe_procs_ht);
    ht_free(&trusted_parents_ht);
    ht_free(&restricted_parents_ht);
    ht_free(&suspicious_children_ht);
}

static void signal_handler(int sig) {
    (void)sig;
    g_running = 0;
}

int main(int argc, char *argv[]) {
    DIR *proc;
    struct dirent *ent;
    int daemon_mode = 0;
    
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-d") == 0 || strcmp(argv[i], "--daemon") == 0)
            daemon_mode = 1;
    }
    
    if (geteuid() != 0) {
        return 1;
    }
    
    g_self_pid = getpid();
    
    signal(SIGPIPE, SIG_IGN);
    signal(SIGTERM, signal_handler);
    signal(SIGINT, signal_handler);
    signal(SIGHUP, SIG_IGN);
    
    prctl(PR_SET_DUMPABLE, 0);
    
    if (daemon_mode) {
        if (daemon(0, 0) < 0) return 1;
        g_self_pid = getpid(); /* Update after daemonizing */
    }
    
    int devnull = open("/dev/null", O_WRONLY);
    if (devnull >= 0) {
        dup2(devnull, STDOUT_FILENO);
        dup2(devnull, STDERR_FILENO);
        close(devnull);
    }
    
    /* Lower scheduling priority */
    setpriority(PRIO_PROCESS, 0, 10);
    
    init_hashtables();
    
    while (g_running) {
        proc = opendir("/proc");
        if (proc) {
            while ((ent = readdir(proc)) != NULL) {
                if (!g_running) break;
                if (isdigit(ent->d_name[0])) {
                    check_process(ent->d_name);
                }
            }
            closedir(proc);
        }
        g_stats.scans_completed++;
        usleep(SCAN_INTERVAL_US);
    }
    
    cleanup_hashtables();
    return 0;
}
