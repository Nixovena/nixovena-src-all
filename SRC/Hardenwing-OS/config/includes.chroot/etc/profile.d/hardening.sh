# Extra Hardened Shell Environment Profile

# 1. Strict File Permissions
# umask 077 means new files are only accessible by the owner (600 for files, 700 for dirs)
umask 077

# 2. Strict Search Path
# Explicitly set PATH to prevent current directory (.) or /tmp/ hijacking.
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# 3. Automatic Logout
# Log out idle shells after 15 minutes (900 seconds) of inactivity.
readonly TMOUT=900
export TMOUT

# 4. Disable Shell History (Anti-Forensics)
# Prevent command history from being saved to disk to avoid leaving traces.
export HISTFILE=/dev/null
export HISTSIZE=0
export HISTFILESIZE=0
# Completely disable history feature for the session
set +o history

# 5. Disable Core Dumps (Shell level)
# Prevent processes started from this shell from dumping core.
ulimit -S -c 0 > /dev/null 2>&1

# 6. Read-only Critical Variables
# Lock these settings so they cannot be re-enabled during the session.
readonly HISTFILE
# readonly HISTSIZE
# readonly HISTFILESIZE
readonly TMOUT

# 7. Shell Aliases for Safety
alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'
alias ln='ln -i'

# 8. Prevent user-level core dumps
ulimit -c 0 > /dev/null 2>&1

# 9. Restrict CC/GCC for non-privileged users
if [ "$(id -u)" -ne 0 ]; then
    alias gcc='echo "ERROR: Compiler access restricted."'
    alias cc='echo "ERROR: Compiler access restricted."'
    alias c++='echo "ERROR: Compiler access restricted."'
    alias make='echo "ERROR: Build tools restricted."'
fi

# Clear history cache on session end
trap "history -c; exit" EXIT
