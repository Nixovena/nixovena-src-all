#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <time.h>
#include <signal.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/fanotify.h>
#include <linux/fanotify.h>
#include <dirent.h>
#include <pthread.h>
#include <stdint.h>
#include <sys/time.h>
#include <sys/resource.h>
#include <sys/prctl.h>
#include <poll.h>
#include <linux/limits.h>

#define PID_HASH_SIZE 16384
#define PID_HASH_MASK (PID_HASH_SIZE - 1)
#define BUCKET_DEPTH 8
#define PROCESS_WATCH_WINDOW_SEC 12
#define MAX_AFFECTED_CALLS 10
#define BASE_DELAY_US 500
#define MAX_DELAY_US 50000
#define JITTER_PROBABILITY 65
#define CLEANUP_INTERVAL_SEC 12
#define IMMUNE_HASH_SIZE 1024
#define IMMUNE_HASH_MASK (IMMUNE_HASH_SIZE - 1)
#define THREAT_DECAY_MS 5000
#define MAX_THREAT_LEVEL 10
#define PATH_WEIGHT_NORMAL 1
#define PATH_WEIGHT_SENSITIVE 3
#define PATH_WEIGHT_CRITICAL 5
#define YOUNG_PROCESS_MS 2000

static const char *SUSPICIOUS_ANCESTRY[] = {
    "sh", "bash", "dash", "zsh", "ksh", "csh", "tcsh", "fish", "ash",
    "python", "python2", "python3", "python2.7", "python3.9", "python3.10",
    "python3.11", "python3.12", "python3.13",
    "perl", "perl5",
    "ruby", "irb", "ruby2.7", "ruby3.0", "ruby3.1", "ruby3.2",
    "php", "php-fpm", "php-cgi", "php7", "php8", "php8.1", "php8.2", "php8.3",
    "lua", "luajit", "lua5.3", "lua5.4",
    "node", "nodejs", "deno", "bun",
    "java", "javac", "dotnet", "mono",
    "nc", "netcat", "ncat", "socat",
    "wget", "curl",
    "ssh", "telnet", "ftp",
    "nginx", "apache2", "httpd", "lighttpd", "caddy",
    "gunicorn", "uwsgi", "uvicorn", "puma", "unicorn",
    "mongod", "redis-server", "memcached",
    "mysqld", "mariadbd", "postgres", "postgresql",
    "base64", "xxd", "od",
    "strace", "ltrace", "gdb",
    "nmap", "masscan",
    NULL
};

static const char *IMMUNE_PROCESSES[] = {
    "systemd", "init", "kthreadd",
    "systemd-journal", "systemd-logind", "systemd-udevd", "systemd-timesyn",
    "systemd-resolve", "systemd-network", "systemd-oomd", "systemd-coredum",
    "systemd-sleep", "systemd-inhibit", "systemd-tmpfile",
    "dbus-daemon", "dbus-broker", "dbus-launch",
    "udevd", "eudev",
    "apt", "apt-get", "dpkg", "aptitude", "synaptic",
    "dpkg-deb", "dpkg-query", "apt-config", "apt-listchanges",
    "unattended-upgr", "debconf", "frontend",
    "pacman", "dnf", "yum", "zypper",
    "flatpak", "flatpak-system-", "snap", "snapd", "snap-confine", "bwrap",
    "sshd", "ssh-agent", "gpg-agent", "gpgv", "gpg",
    "openssl", "pinentry", "gnome-keyring-d", "seahorse", "secret-tool",
    "polkitd", "sudo", "su", "doas", "pkexec", "run0",
    "pam", "pam_unix",
    "firefox", "firefox-esr", "firefox-bin",
    "chromium", "chromium-browse", "chrome", "google-chrome",
    "brave", "brave-browser",
    "Web Content", "Isolated Web Co", "Socket Process",
    "Privileged Cont", "RDD Process", "Utility Process",
    "WebExtensions", "GeckoMain", "GPU Process",
    "librewolf", "waterfox", "pale-moon", "falkon",
    "Xorg", "X", "Xwayland", "weston", "sway",
    "gnome-shell", "gnome-session", "mutter", "gnome-settings-",
    "gnome-control-c", "gnome-terminal-", "gnome-software",
    "nautilus", "baobab", "evince", "eog", "gedit", "totem",
    "gjs", "gsd-", "gvfsd", "gvfs-", "tracker-miner", "tracker-store",
    "evolution", "evolution-calen", "evolution-addre",
    "plasmashell", "kwin_x11", "kwin_wayland", "kded5", "kded6",
    "dolphin", "kate", "konsole", "krunner", "kwalletd",
    "baloo_file", "kscreen_backend", "polkit-kde-auth",
    "kglobalaccel5", "kactivitymanag", "ksmserver", "knotify",
    "xfce4-session", "xfwm4", "xfce4-panel", "xfce4-terminal",
    "xfce4-settings-", "xfce4-power-man", "xfce4-notifyd",
    "thunar", "mousepad", "ristretto", "xfdesktop",
    "mate-session", "mate-panel", "mate-terminal", "mate-settings-d",
    "mate-power-mana", "mate-screensave",
    "caja", "pluma", "atril",
    "gdm", "gdm3", "lightdm", "sddm", "xdm",
    "picom", "compton", "xcompmgr",
    "pulseaudio", "pipewire", "wireplumber", "pipewire-pulse",
    "pipewire-media-", "alsa", "jackd",
    "NetworkManager", "wpa_supplicant", "avahi-daemon",
    "dhclient", "dhcpcd", "iwd", "connmand", "ModemManager",
    "openvpn", "wireguard", "wg-quick", "openconnect",
    "qemu-system-x86", "qemu-system-aa", "libvirtd", "virtqemud",
    "virt-manager", "VBoxSVC", "VBoxXPCOMIPCD", "VBoxHeadless",
    "vmtoolsd", "spice-vdagent",
    "dockerd", "containerd", "containerd-shim", "podman", "crio",
    "cron", "anacron", "atd", "rsyslogd", "syslogd", "journald",
    "sshd", "login", "agetty", "getty", "logrotate",
    "irqbalance", "thermald", "acpid", "upowerd", "upower",
    "accounts-daemon", "rtkit-daemon", "udisksd", "colord",
    "cupsd", "cups-browsed", "lpd",
    "bluetoothd", "blueman-applet", "blueman-manage", "obexd",
    "at-spi-bus-laun", "at-spi2-registr", "orca",
    "ibus-daemon", "ibus-x11", "ibus-portal", "fcitx5", "fcitx",
    "thunderbird", "electron", "code", "visual-studio-code",
    "discord", "spotify", "slack", "telegram-deskto", "zoom",
    "alacritty", "kitty", "foot", "wezterm", "tilix",
    "xterm", "urxvt", "st", "sakura", "terminator", "guake", "yakuake",
    "vim", "nvim", "nano", "emacs", "micro", "helix",
    "sublime_text", "geany", "atom",
    "nemo", "pcmanfm", "spacefm", "ranger", "mc",
    "mpv", "vlc", "celluloid", "parole", "rhythmbox", "lollypop",
    "audacious", "clementine",
    "feh", "sxiv", "nsxiv", "imv", "gimp", "inkscape",
    "okular", "zathura", "mupdf", "libreoffice",
    "htop", "btop", "top", "iotop",
    "xz", "gzip", "bzip2", "zstd", "lz4", "pigz", "unzip", "tar", "cpio",
    "xdg-desktop-por", "xdg-document-po", "xdg-permission-",
    "flatpak-session", "portal",
    "calamares", "live-config", "live-boot",
    "xennytsu", "poison", "silencer",
    NULL
};

static const char *EXPLOIT_CMDLINE_PATTERNS[] = {
    "/dev/tcp/", "/dev/udp/",
    "base64 -d", "base64 --decode",
    "stratum+tcp", "stratum+ssl",
    "nc -e", "nc -c", "ncat -e",
    "bash -i >&",
    "python -c 'import socket",
    "python3 -c 'import socket",
    "perl -e 'use Socket",
    "ruby -rsocket",
    "php -r '$sock=fsockopen",
    "socat exec:", "socat tcp:",
    "curl | bash", "curl | sh",
    "wget -O - | bash", "wget -O - | sh",
    "eval \"$(", "eval '$(", "eval `",
    NULL
};

typedef struct {
    pid_t pid;
    uint64_t first_seen_ms;
    uint64_t last_access_ms;
    uint16_t total_accesses;
    uint8_t affected_count;
    uint8_t threat_level;
    uint8_t is_target;
    uint8_t is_immune;
    uint8_t has_exploit_cmdline;
    uint8_t path_weight;
} PidEntry;

typedef struct {
    PidEntry entries[BUCKET_DEPTH];
    uint8_t count;
} PidBucket;

static PidBucket pid_table[PID_HASH_SIZE];
static pthread_rwlock_t table_rwlock = PTHREAD_RWLOCK_INITIALIZER;
static int fan_fd = -1;
static volatile sig_atomic_t running = 1;
static pid_t self_pid = 0;

typedef struct ImmuneNode {
    const char *key;
    struct ImmuneNode *next;
} ImmuneNode;

static ImmuneNode *immune_ht[IMMUNE_HASH_SIZE] = {0};

static uint32_t djb2_hash(const char *str) {
    uint32_t hash = 5381;
    int c;
    while ((c = *str++))
        hash = ((hash << 5) + hash) + c;
    return hash;
}

static void immune_ht_init(void) {
    for (int i = 0; IMMUNE_PROCESSES[i]; i++) {
        uint32_t idx = djb2_hash(IMMUNE_PROCESSES[i]) & IMMUNE_HASH_MASK;
        ImmuneNode *e = malloc(sizeof(ImmuneNode));
        if (!e) continue;
        e->key = IMMUNE_PROCESSES[i];
        e->next = immune_ht[idx];
        immune_ht[idx] = e;
    }
}

static int immune_ht_lookup(const char *key) {
    if (!key) return 0;
    uint32_t idx = djb2_hash(key) & IMMUNE_HASH_MASK;
    ImmuneNode *e = immune_ht[idx];
    while (e) {
        if (strcmp(e->key, key) == 0) return 1;
        e = e->next;
    }
    return 0;
}

static int immune_substr_match(const char *comm) {
    for (int i = 0; IMMUNE_PROCESSES[i]; i++) {
        if (strstr(comm, IMMUNE_PROCESSES[i])) return 1;
    }
    return 0;
}

static uint64_t monotonic_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC_COARSE, &ts);
    return (uint64_t)ts.tv_sec * 1000ULL + (uint64_t)ts.tv_nsec / 1000000ULL;
}

static int read_proc_comm(pid_t pid, char *buf, size_t size) {
    char path[64];
    snprintf(path, sizeof(path), "/proc/%d/comm", pid);
    int fd = open(path, O_RDONLY);
    if (fd < 0) return -1;
    int len = read(fd, buf, size - 1);
    close(fd);
    if (len <= 0) return -1;
    buf[len] = '\0';
    char *nl = strchr(buf, '\n');
    if (nl) *nl = '\0';
    return 0;
}

static pid_t read_proc_ppid(pid_t pid) {
    char path[64], buf[512];
    snprintf(path, sizeof(path), "/proc/%d/stat", pid);
    int fd = open(path, O_RDONLY);
    if (fd < 0) return -1;
    ssize_t len = read(fd, buf, sizeof(buf) - 1);
    close(fd);
    if (len <= 0) return -1;
    buf[len] = '\0';
    char *p = strrchr(buf, ')');
    if (!p) return -1;
    p += 2;
    char state;
    pid_t ppid = -1;
    if (sscanf(p, "%c %d", &state, &ppid) < 2) return -1;
    return ppid;
}

static uid_t read_proc_uid(pid_t pid) {
    char path[64], line[256];
    snprintf(path, sizeof(path), "/proc/%d/status", pid);
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    uid_t uid = 0;
    while (fgets(line, sizeof(line), f)) {
        if (strncmp(line, "Uid:", 4) == 0) {
            sscanf(line + 4, "%u", &uid);
            break;
        }
    }
    fclose(f);
    return uid;
}

static int str_in_list(const char *str, const char **list) {
    if (!str) return 0;
    for (int i = 0; list[i]; i++) {
        if (strcmp(str, list[i]) == 0) return 1;
    }
    return 0;
}

static int check_exploit_cmdline(pid_t pid) {
    char path[64], buf[4096];
    snprintf(path, sizeof(path), "/proc/%d/cmdline", pid);
    int fd = open(path, O_RDONLY);
    if (fd < 0) return 0;
    ssize_t len = read(fd, buf, sizeof(buf) - 1);
    close(fd);
    if (len <= 0) return 0;
    buf[len] = '\0';
    for (int i = 0; i < len - 1; i++) {
        if (buf[i] == '\0') buf[i] = ' ';
    }
    for (int i = 0; EXPLOIT_CMDLINE_PATTERNS[i]; i++) {
        if (strstr(buf, EXPLOIT_CMDLINE_PATTERNS[i])) return 1;
    }
    return 0;
}

static int check_exe_in_tmpfs(pid_t pid) {
    char path[64], link[PATH_MAX];
    snprintf(path, sizeof(path), "/proc/%d/exe", pid);
    ssize_t len = readlink(path, link, sizeof(link) - 1);
    if (len <= 0) return 0;
    link[len] = '\0';
    if (strstr(link, "/tmp/") || strstr(link, "/dev/shm/") ||
        strstr(link, "/var/tmp/") || strstr(link, "memfd:"))
        return 1;
    return 0;
}

static int has_suspicious_parent(pid_t pid, int max_depth) {
    char comm[64];
    pid_t current = pid;
    for (int depth = 0; depth < max_depth && current > 1; depth++) {
        pid_t parent = read_proc_ppid(current);
        if (parent <= 1) break;
        if (read_proc_comm(parent, comm, sizeof(comm)) == 0) {
            if (str_in_list(comm, SUSPICIOUS_ANCESTRY)) return 1;
        }
        current = parent;
    }
    return 0;
}

static int evaluate_process(pid_t pid, uint8_t *out_exploit, uint8_t *out_initial_threat) {
    char comm[64];
    *out_exploit = 0;
    *out_initial_threat = 0;

    if (read_proc_comm(pid, comm, sizeof(comm)) < 0) return 0;
    if (immune_ht_lookup(comm)) return 0;
    if (immune_substr_match(comm)) return 0;
    if (read_proc_uid(pid) == 0) return 0;

    int target = 0;

    if (check_exploit_cmdline(pid)) {
        *out_exploit = 1;
        *out_initial_threat = 5;
        target = 1;
    }

    if (check_exe_in_tmpfs(pid)) {
        *out_initial_threat += 3;
        target = 1;
    }

    if (str_in_list(comm, SUSPICIOUS_ANCESTRY)) {
        if (*out_initial_threat == 0) *out_initial_threat = 1;
        target = 1;
    }

    if (!target && has_suspicious_parent(pid, 4)) {
        *out_initial_threat = 1;
        target = 1;
    }

    return target;
}

static int is_immune_process(pid_t pid) {
    char comm[64];
    if (read_proc_comm(pid, comm, sizeof(comm)) < 0) return 1;
    if (immune_ht_lookup(comm)) return 1;
    if (immune_substr_match(comm)) return 1;
    if (read_proc_uid(pid) == 0) return 1;
    return 0;
}

static int resolve_fd_path_weight(int fd) {
    char fdpath[64], link[PATH_MAX];
    snprintf(fdpath, sizeof(fdpath), "/proc/self/fd/%d", fd);
    ssize_t len = readlink(fdpath, link, sizeof(link) - 1);
    if (len <= 0) return PATH_WEIGHT_NORMAL;
    link[len] = '\0';

    if (strstr(link, "/dev/mem") || strstr(link, "/dev/kmem") ||
        strstr(link, "/dev/port") || strstr(link, "/proc/self/mem") ||
        strstr(link, "/proc/self/pagemap") || strstr(link, "/proc/kcore"))
        return PATH_WEIGHT_CRITICAL;

    if (strstr(link, "/proc/self/maps") || strstr(link, "/proc/self/status") ||
        strstr(link, "/proc/sys/kernel/") || strstr(link, "/etc/shadow") ||
        strstr(link, "/etc/passwd"))
        return PATH_WEIGHT_SENSITIVE;

    return PATH_WEIGHT_NORMAL;
}

static PidEntry* pid_lookup(pid_t pid) {
    uint32_t idx = (uint32_t)pid & PID_HASH_MASK;
    PidBucket *b = &pid_table[idx];
    for (int i = 0; i < b->count; i++) {
        if (b->entries[i].pid == pid) return &b->entries[i];
    }
    return NULL;
}

static PidEntry* pid_insert(pid_t pid) {
    uint32_t idx = (uint32_t)pid & PID_HASH_MASK;
    PidBucket *b = &pid_table[idx];

    if (b->count < BUCKET_DEPTH) {
        PidEntry *e = &b->entries[b->count++];
        memset(e, 0, sizeof(PidEntry));
        e->pid = pid;
        e->first_seen_ms = monotonic_ms();
        return e;
    }

    uint64_t now = monotonic_ms();
    int oldest = 0;
    uint64_t oldest_time = b->entries[0].first_seen_ms;
    for (int i = 1; i < BUCKET_DEPTH; i++) {
        if (b->entries[i].first_seen_ms < oldest_time) {
            oldest_time = b->entries[i].first_seen_ms;
            oldest = i;
        }
    }

    if ((now - oldest_time) > (PROCESS_WATCH_WINDOW_SEC * 2000ULL)) {
        PidEntry *e = &b->entries[oldest];
        memset(e, 0, sizeof(PidEntry));
        e->pid = pid;
        e->first_seen_ms = now;
        return e;
    }

    return NULL;
}

static PidEntry* get_or_create_entry(pid_t pid, int event_fd) {
    pthread_rwlock_rdlock(&table_rwlock);
    PidEntry *e = pid_lookup(pid);
    if (e) {
        e->total_accesses++;
        e->last_access_ms = monotonic_ms();
        if (event_fd >= 0) {
            int w = resolve_fd_path_weight(event_fd);
            if (w > e->path_weight) e->path_weight = w;
        }
        pthread_rwlock_unlock(&table_rwlock);
        return e;
    }
    pthread_rwlock_unlock(&table_rwlock);

    pthread_rwlock_wrlock(&table_rwlock);
    e = pid_lookup(pid);
    if (!e) {
        e = pid_insert(pid);
        if (e) {
            if (is_immune_process(pid)) {
                e->is_immune = 1;
                e->is_target = 0;
            } else {
                uint8_t exploit_flag = 0, initial_threat = 0;
                e->is_target = evaluate_process(pid, &exploit_flag, &initial_threat);
                e->has_exploit_cmdline = exploit_flag;
                e->threat_level = initial_threat;
            }
            e->last_access_ms = e->first_seen_ms;
            if (event_fd >= 0) {
                e->path_weight = resolve_fd_path_weight(event_fd);
            }
        }
    }
    pthread_rwlock_unlock(&table_rwlock);
    return e;
}

static void cleanup_dead_entries(void) {
    char path[32];
    pthread_rwlock_wrlock(&table_rwlock);
    for (int i = 0; i < PID_HASH_SIZE; i++) {
        PidBucket *b = &pid_table[i];
        int j = 0;
        while (j < b->count) {
            snprintf(path, sizeof(path), "/proc/%d", b->entries[j].pid);
            if (access(path, F_OK) != 0) {
                b->entries[j] = b->entries[b->count - 1];
                b->count--;
            } else {
                j++;
            }
        }
    }
    pthread_rwlock_unlock(&table_rwlock);
}

static useconds_t calculate_adaptive_delay(PidEntry *entry) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC_COARSE, &ts);
    unsigned int seed = (unsigned int)(ts.tv_nsec ^ ((uint64_t)entry->pid * 2654435761ULL));

    uint64_t age_ms = monotonic_ms() - entry->first_seen_ms;
    int young_multiplier = (age_ms < YOUNG_PROCESS_MS) ? 3 : 1;

    int threat_mult = 1 + entry->threat_level;
    int path_mult = entry->path_weight;
    int exploit_mult = entry->has_exploit_cmdline ? 3 : 1;

    useconds_t base = BASE_DELAY_US;
    useconds_t scaled = base * threat_mult * path_mult * exploit_mult * young_multiplier;

    useconds_t jitter = rand_r(&seed) % (scaled / 2 + 1);
    useconds_t delay = scaled + jitter;

    if (delay > MAX_DELAY_US) delay = MAX_DELAY_US;
    if (delay < BASE_DELAY_US) delay = BASE_DELAY_US;

    return delay;
}

static void escalate_threat(PidEntry *entry) {
    uint64_t now = monotonic_ms();
    uint64_t since_last = now - entry->last_access_ms;

    if (since_last < THREAT_DECAY_MS) {
        if (entry->threat_level < MAX_THREAT_LEVEL)
            entry->threat_level++;
    } else if (since_last > THREAT_DECAY_MS * 3 && entry->threat_level > 0) {
        entry->threat_level--;
    }
}

static int should_apply_delay(PidEntry *entry) {
    if (!entry || !entry->is_target || entry->is_immune) return 0;
    uint64_t age_ms = monotonic_ms() - entry->first_seen_ms;
    if (age_ms > (PROCESS_WATCH_WINDOW_SEC * 1000ULL)) {
        if (!entry->has_exploit_cmdline && entry->threat_level < 5)
            return 0;
    }
    if (entry->affected_count >= MAX_AFFECTED_CALLS) {
        if (!entry->has_exploit_cmdline)
            return 0;
    }
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC_COARSE, &ts);
    unsigned int seed = (unsigned int)(ts.tv_nsec ^ entry->pid);
    int prob = JITTER_PROBABILITY;
    if (entry->has_exploit_cmdline) prob = 95;
    else if (entry->threat_level >= 5) prob = 90;
    else if (entry->path_weight >= PATH_WEIGHT_CRITICAL) prob = 85;
    if ((rand_r(&seed) % 100) >= prob) return 0;
    return 1;
}

static void apply_delay(PidEntry *entry) {
    escalate_threat(entry);
    if (!should_apply_delay(entry)) return;
    entry->affected_count++;
    useconds_t delay = calculate_adaptive_delay(entry);
    usleep(delay);
}

static int init_monitoring(void) {
    fan_fd = fanotify_init(
        FAN_CLASS_CONTENT | FAN_CLOEXEC | FAN_NONBLOCK,
        O_RDONLY | O_LARGEFILE
    );
    if (fan_fd < 0) return -1;

    int use_perm = 0;
    if (fanotify_mark(fan_fd, FAN_MARK_ADD,
                      FAN_OPEN_PERM | FAN_ACCESS_PERM,
                      AT_FDCWD, "/dev/urandom") >= 0) {
        use_perm = 1;
    } else {
        if (fanotify_mark(fan_fd, FAN_MARK_ADD,
                          FAN_OPEN | FAN_ACCESS,
                          AT_FDCWD, "/dev/urandom") < 0) {
            close(fan_fd);
            fan_fd = -1;
            return -1;
        }
    }

    unsigned int flags = use_perm
        ? (FAN_OPEN_PERM | FAN_ACCESS_PERM)
        : (FAN_OPEN | FAN_ACCESS);

    const char *monitored_paths[] = {
        "/dev/random",
        "/dev/mem",
        "/dev/kmem",
        "/dev/port",
        "/proc/self/mem",
        "/proc/self/maps",
        "/proc/self/pagemap",
        "/proc/kcore",
        "/proc/kallsyms",
        "/proc/modules",
        "/etc/shadow",
        "/etc/sudoers",
        "/proc/sys/kernel/core_pattern",
        "/proc/sys/kernel/modprobe",
        "/proc/sys/vm/dirty_ratio",
        "/proc/sysrq-trigger",
        NULL
    };

    for (int i = 0; monitored_paths[i]; i++) {
        if (access(monitored_paths[i], F_OK) == 0)
            fanotify_mark(fan_fd, FAN_MARK_ADD, flags, AT_FDCWD, monitored_paths[i]);
    }

    unsigned int dir_flags = use_perm
        ? (FAN_OPEN_PERM | FAN_CLOSE_WRITE)
        : (FAN_OPEN | FAN_CLOSE_WRITE);

    const char *staging_dirs[] = {
        "/tmp",
        "/dev/shm",
        "/var/tmp",
        "/run/shm",
        NULL
    };

    for (int i = 0; staging_dirs[i]; i++) {
        struct stat st;
        if (stat(staging_dirs[i], &st) == 0 && S_ISDIR(st.st_mode))
            fanotify_mark(fan_fd, FAN_MARK_ADD | FAN_MARK_MOUNT, dir_flags,
                         AT_FDCWD, staging_dirs[i]);
    }

    return 0;
}

static void handle_event(struct fanotify_event_metadata *event) {
    if (!event || event->fd < 0) return;
    if (event->pid == self_pid || event->pid <= 1) {
        if (event->mask & (FAN_OPEN_PERM | FAN_ACCESS_PERM)) {
            struct fanotify_response r = { .fd = event->fd, .response = FAN_ALLOW };
            write(fan_fd, &r, sizeof(r));
        }
        close(event->fd);
        return;
    }

    PidEntry *entry = get_or_create_entry(event->pid, event->fd);

    if (entry && entry->is_target && !entry->is_immune)
        apply_delay(entry);

    if (event->mask & (FAN_OPEN_PERM | FAN_ACCESS_PERM)) {
        struct fanotify_response r = { .fd = event->fd, .response = FAN_ALLOW };
        write(fan_fd, &r, sizeof(r));
    }

    close(event->fd);
}

static void* cleanup_worker(void *arg) {
    (void)arg;
    int elapsed = 0;
    while (running) {
        sleep(1);
        elapsed++;
        if (elapsed >= CLEANUP_INTERVAL_SEC) {
            elapsed = 0;
            cleanup_dead_entries();
        }
    }
    return NULL;
}

static void signal_handler(int sig) {
    (void)sig;
    running = 0;
}

int main(int argc, char *argv[]) {
    pthread_t cleanup_tid;
    char event_buf[16384];
    int daemon_mode = 0;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-d") == 0 || strcmp(argv[i], "--daemon") == 0)
            daemon_mode = 1;
    }

    if (geteuid() != 0) return 1;

    self_pid = getpid();

    signal(SIGPIPE, SIG_IGN);
    signal(SIGTERM, signal_handler);
    signal(SIGINT, signal_handler);
    signal(SIGHUP, SIG_IGN);

    prctl(PR_SET_DUMPABLE, 0);

    if (daemon_mode) {
        if (daemon(0, 0) < 0) return 1;
        self_pid = getpid(); /* Update after daemonizing */
    }

    int devnull = open("/dev/null", O_WRONLY);
    if (devnull >= 0) {
        dup2(devnull, STDOUT_FILENO);
        dup2(devnull, STDERR_FILENO);
        close(devnull);
    }

    setpriority(PRIO_PROCESS, 0, 10);
    immune_ht_init();

    if (init_monitoring() < 0) return 1;

    pthread_create(&cleanup_tid, NULL, cleanup_worker, NULL);

    struct pollfd pfd = { .fd = fan_fd, .events = POLLIN };

    while (running) {
        int ret = poll(&pfd, 1, 1000);
        if (ret < 0) {
            if (errno == EINTR) continue;
            break;
        }
        if (ret > 0 && (pfd.revents & POLLIN)) {
            ssize_t len = read(fan_fd, event_buf, sizeof(event_buf));
            if (len > 0) {
                struct fanotify_event_metadata *event =
                    (struct fanotify_event_metadata *)event_buf;
                while (FAN_EVENT_OK(event, len)) {
                    if (!(event->mask & FAN_Q_OVERFLOW))
                        handle_event(event);
                    event = FAN_EVENT_NEXT(event, len);
                }
            }
        }
    }

    pthread_join(cleanup_tid, NULL);
    if (fan_fd >= 0) close(fan_fd);

    /* Cleanup immune hash table */
    for (int i = 0; i < IMMUNE_HASH_SIZE; i++) {
        ImmuneNode *node = immune_ht[i];
        while (node) {
            ImmuneNode *next = node->next;
            free(node);
            node = next;
        }
        immune_ht[i] = NULL;
    }

    return 0;
}
