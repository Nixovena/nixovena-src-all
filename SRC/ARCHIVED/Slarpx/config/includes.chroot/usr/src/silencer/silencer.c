#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <signal.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <sys/mount.h>
#include <dirent.h>
#include <stdint.h>
#include <time.h>

#define ENFORCE_INTERVAL_SEC 30
#define TAMPER_CHECK_SEC 5

static volatile sig_atomic_t running = 1;

typedef struct {
    const char *path;
    mode_t mode;
} PermRule;

static const PermRule PROC_PERMS[] = {
    {"/proc/kallsyms", 0400},
    {"/proc/kcore", 0400},
    {"/proc/modules", 0400},
    {"/proc/slabinfo", 0400},
    {"/proc/config.gz", 0400},
    {"/proc/sched_debug", 0400},
    {"/proc/timer_list", 0400},
    {"/proc/timer_stats", 0400},
    {"/proc/buddyinfo", 0400},
    {"/proc/pagetypeinfo", 0400},
    {"/proc/vmallocinfo", 0400},
    {"/proc/zoneinfo", 0400},
    {"/proc/softirqs", 0400},
    {"/proc/diskstats", 0440},
    {"/proc/partitions", 0440},
    {"/proc/version", 0444},
    {"/proc/cmdline", 0400},
    {"/proc/keys", 0400},
    {"/proc/key-users", 0400},
    {"/proc/consoles", 0400},
    {"/proc/iomem", 0400},
    {"/proc/ioports", 0400},
    {"/proc/sysrq-trigger", 0600},
    {"/proc/kpagecount", 0400},
    {"/proc/kpageflags", 0400},
    {"/proc/kmsg", 0400},
    {"/proc/schedstat", 0400},
    {NULL, 0}
};

static const PermRule BOOT_PERMS[] = {
    {"/usr/src", 0750},
    {"/lib/modules", 0750},
    {"/boot", 0700},
    {NULL, 0}
};

typedef struct {
    const char *path;
    const char *value;
} TamperGuard;

static const TamperGuard CRITICAL_GUARDS[] = {
    {"/proc/sys/kernel/dmesg_restrict", "1"},
    {"/proc/sys/kernel/kptr_restrict", "2"},
    {"/proc/sys/kernel/yama/ptrace_scope", "3"},
    {"/proc/sys/kernel/unprivileged_bpf_disabled", "1"},
    {"/proc/sys/kernel/randomize_va_space", "2"},
    {"/proc/sys/kernel/sysrq", "0"},
    {"/proc/sys/kernel/kexec_load_disabled", "1"},
    {"/proc/sys/fs/suid_dumpable", "0"},
    {"/proc/sys/fs/protected_hardlinks", "1"},
    {"/proc/sys/fs/protected_symlinks", "1"},
    {"/proc/sys/fs/protected_fifos", "2"},
    {"/proc/sys/fs/protected_regular", "2"},
    {"/proc/sys/net/core/bpf_jit_harden", "2"},
    {"/proc/sys/dev/tty/ldisc_autoload", "0"},
    {"/proc/sys/kernel/core_pattern", "|/bin/false"},
    {"/proc/sys/kernel/printk", "3 3 3 3"},
    {"/proc/sys/kernel/perf_event_paranoid", "3"},
    {"/proc/sys/kernel/panic_on_oops", "1"},
    {NULL, NULL}
};

static int write_to_path(const char *path, const char *value) {
    int fd = open(path, O_WRONLY | O_TRUNC);
    if (fd < 0) return -1;
    ssize_t len = (ssize_t)strlen(value);
    ssize_t w = write(fd, value, (size_t)len);
    close(fd);
    return (w == len) ? 0 : -1;
}

static int read_from_path(const char *path, char *buf, size_t size) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) return -1;
    ssize_t len = read(fd, buf, size - 1);
    close(fd);
    if (len <= 0) return -1;
    buf[len] = '\0';
    char *nl = strchr(buf, '\n');
    if (nl) *nl = '\0';
    return 0;
}

static void enforce_proc_permissions(void) {
    for (int i = 0; PROC_PERMS[i].path; i++) {
        if (access(PROC_PERMS[i].path, F_OK) == 0)
            chmod(PROC_PERMS[i].path, PROC_PERMS[i].mode);
    }
}

static void enforce_boot_permissions(void) {
    for (int i = 0; BOOT_PERMS[i].path; i++) {
        if (access(BOOT_PERMS[i].path, F_OK) == 0)
            chmod(BOOT_PERMS[i].path, BOOT_PERMS[i].mode);
    }

    const char *patterns[] = {"vmlinuz", "System.map", "config-", "initrd", NULL};
    DIR *dir = opendir("/boot");
    if (dir) {
        struct dirent *ent;
        while ((ent = readdir(dir))) {
            for (int i = 0; patterns[i]; i++) {
                if (strncmp(ent->d_name, patterns[i], strlen(patterns[i])) == 0) {
                    char path[512];
                    snprintf(path, sizeof(path), "/boot/%s", ent->d_name);
                    chmod(path, 0400);
                }
            }
        }
        closedir(dir);
    }
}

static void lockdown_debugfs(void) {
    const char *paths[] = {
        "/sys/kernel/debug",
        "/sys/kernel/tracing",
        "/sys/kernel/security",
        NULL
    };
    for (int i = 0; paths[i]; i++) {
        struct stat st;
        if (stat(paths[i], &st) == 0 && S_ISDIR(st.st_mode))
            chmod(paths[i], 0700);
    }
}

static void restrict_coredumps(void) {
    struct rlimit rl = { .rlim_cur = 0, .rlim_max = 0 };
    setrlimit(RLIMIT_CORE, &rl);
}

static void clear_dmesg_buffer(void) {
    pid_t pid = fork();
    if (pid == 0) {
        int devnull = open("/dev/null", O_RDWR);
        if (devnull >= 0) {
            dup2(devnull, 0);
            dup2(devnull, 1);
            dup2(devnull, 2);
            close(devnull);
        }
        execl("/bin/dmesg", "dmesg", "-C", NULL);
        _exit(1);
    }
    if (pid > 0) {
        int status;
        waitpid(pid, &status, 0);
    }
}

static void hide_process_info(void) {
    /* Remount /proc with hidepid=invisible (kernel 5.8+) to hide other users' processes.
     * hidepid=invisible is preferred over hidepid=2 because:
     * - It works correctly with systemd and polkit
     * - Desktop tools (htop, system-monitor) still work for root
     * - It doesn't break /proc/PID/stat access needed by ps
     * Falls back to hidepid=2 if invisible is not supported. */
    if (mount("proc", "/proc", "proc", MS_REMOUNT, "hidepid=invisible,gid=0") != 0) {
        mount("proc", "/proc", "proc", MS_REMOUNT, "hidepid=2,gid=0");
    }
}

static void restrict_kernel_module_paths(void) {
    DIR *dir = opendir("/lib/modules");
    if (!dir) return;
    struct dirent *ent;
    while ((ent = readdir(dir))) {
        if (ent->d_name[0] == '.') continue;
        char path[512];
        snprintf(path, sizeof(path), "/lib/modules/%s/build", ent->d_name);
        if (access(path, F_OK) == 0) chmod(path, 0700);
        snprintf(path, sizeof(path), "/lib/modules/%s/source", ent->d_name);
        if (access(path, F_OK) == 0) chmod(path, 0700);
    }
    closedir(dir);
}

static void restrict_etc_sensitive(void) {
    const PermRule etc_files[] = {
        {"/etc/shadow", 0600},
        {"/etc/shadow-", 0600},
        {"/etc/gshadow", 0600},
        {"/etc/gshadow-", 0600},
        {"/etc/sudoers", 0440},
        {"/etc/ssh/sshd_config", 0600},
        {"/etc/crypttab", 0600},
        {"/etc/security/opasswd", 0600},
        {"/etc/security/access.conf", 0600},
        {"/etc/crontab", 0600},
        {NULL, 0}
    };
    for (int i = 0; etc_files[i].path; i++) {
        if (access(etc_files[i].path, F_OK) == 0)
            chmod(etc_files[i].path, etc_files[i].mode);
    }
}

static void restrict_compiler_tools(void) {
    const char *tools[] = {
        "/usr/bin/gcc", "/usr/bin/g++", "/usr/bin/cc",
        "/usr/bin/make", "/usr/bin/as", "/usr/bin/ld",
        "/usr/bin/objdump", "/usr/bin/readelf", "/usr/bin/nm",
        "/usr/bin/strings", "/usr/bin/strace", "/usr/bin/ltrace",
        "/usr/bin/gdb", "/usr/bin/nasm",
        "/usr/bin/clang", "/usr/bin/clang++",
        "/usr/bin/objcopy", "/usr/bin/strip",
        NULL
    };
    for (int i = 0; tools[i]; i++) {
        if (access(tools[i], F_OK) == 0)
            chmod(tools[i], 0750);
    }
}

static void restrict_network_tools(void) {
    const char *tools[] = {
        "/usr/bin/nmap", "/usr/bin/masscan",
        "/usr/bin/tcpdump", "/usr/sbin/tcpdump",
        "/usr/bin/wireshark", "/usr/bin/tshark",
        "/usr/bin/hping3", "/usr/bin/arping",
        "/usr/sbin/arpwatch",
        "/usr/bin/ettercap", "/usr/bin/bettercap",
        "/usr/bin/aircrack-ng", "/usr/bin/airmon-ng",
        "/usr/bin/kismet",
        NULL
    };
    for (int i = 0; tools[i]; i++) {
        if (access(tools[i], F_OK) == 0)
            chmod(tools[i], 0750);
    }
}

static void restrict_world_readable_logs(void) {
    const char *logs[] = {
        "/var/log/auth.log",
        "/var/log/syslog",
        "/var/log/kern.log",
        "/var/log/daemon.log",
        "/var/log/debug",
        "/var/log/messages",
        "/var/log/user.log",
        "/var/log/mail.log",
        "/var/log/dmesg",
        "/var/log/boot.log",
        "/var/log/faillog",
        "/var/log/btmp",
        "/var/log/wtmp",
        "/var/log/lastlog",
        "/var/log/dpkg.log",
        "/var/log/alternatives.log",
        NULL
    };
    for (int i = 0; logs[i]; i++) {
        if (access(logs[i], F_OK) == 0)
            chmod(logs[i], 0640);
    }
}

static void restrict_suid_sgid_binaries(void) {
    /* Restrict dangerous SUID binaries that are commonly exploited */
    const char *dangerous_suids[] = {
        "/usr/bin/chfn",
        "/usr/bin/chsh",
        "/usr/bin/newgrp",
        "/usr/sbin/unix_chkpwd",
        NULL
    };
    for (int i = 0; dangerous_suids[i]; i++) {
        struct stat st;
        if (stat(dangerous_suids[i], &st) == 0) {
            if (st.st_mode & (S_ISUID | S_ISGID)) {
                /* Remove SUID/SGID but keep executable */
                chmod(dangerous_suids[i], st.st_mode & ~(S_ISUID | S_ISGID));
            }
        }
    }
}

static int tamper_check(void) {
    int tampered = 0;
    char buf[256];
    for (int i = 0; CRITICAL_GUARDS[i].path; i++) {
        if (access(CRITICAL_GUARDS[i].path, F_OK) != 0) continue;
        if (read_from_path(CRITICAL_GUARDS[i].path, buf, sizeof(buf)) == 0) {
            if (strcmp(buf, CRITICAL_GUARDS[i].value) != 0) {
                write_to_path(CRITICAL_GUARDS[i].path, CRITICAL_GUARDS[i].value);
                tampered = 1;
            }
        }
    }
    return tampered;
}

static void initial_hardening(void) {
    enforce_proc_permissions();
    enforce_boot_permissions();
    lockdown_debugfs();
    restrict_coredumps();
    hide_process_info();
    restrict_kernel_module_paths();
    restrict_etc_sensitive();
    restrict_compiler_tools();
    restrict_network_tools();
    restrict_world_readable_logs();
    restrict_suid_sgid_binaries();
    clear_dmesg_buffer();
    tamper_check();
}

static void signal_handler(int sig) {
    (void)sig;
    running = 0;
}

int main(int argc, char *argv[]) {
    int daemon_mode = 0;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-d") == 0 || strcmp(argv[i], "--daemon") == 0)
            daemon_mode = 1;
    }

    if (geteuid() != 0) return 1;

    signal(SIGPIPE, SIG_IGN);
    signal(SIGTERM, signal_handler);
    signal(SIGINT, signal_handler);
    signal(SIGHUP, SIG_IGN);

    prctl(PR_SET_DUMPABLE, 0);

    if (daemon_mode) {
        if (daemon(0, 0) < 0) return 1;
    }

    int devnull = open("/dev/null", O_WRONLY);
    if (devnull >= 0) {
        dup2(devnull, STDOUT_FILENO);
        dup2(devnull, STDERR_FILENO);
        close(devnull);
    }

    initial_hardening();

    int enforce_counter = 0;

    while (running) {
        sleep(TAMPER_CHECK_SEC);

        tamper_check();

        enforce_counter += TAMPER_CHECK_SEC;
        if (enforce_counter >= ENFORCE_INTERVAL_SEC) {
            enforce_counter = 0;
            enforce_proc_permissions();
            enforce_boot_permissions();
            lockdown_debugfs();
            restrict_world_readable_logs();
            restrict_etc_sensitive();
            restrict_suid_sgid_binaries();
        }
    }

    return 0;
}
