# fix for screen readers
if grep -Fqa 'accessibility=' /proc/cmdline &> /dev/null; then
    setopt SINGLE_LINE_ZLE
fi

~/.automated_script.sh

# Auto-start the minimal Openbox session on tty1 if no X server is already running.
if [[ -z "$DISPLAY" ]] && [[ "$(tty)" = "/dev/tty1" ]] && ! grep -Fqa 'nox=' /proc/cmdline &>/dev/null; then
    exec startx -- -keeptty &>/dev/null
fi
