#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

# System Aliases
alias ls='ls --color=auto'
alias grep='grep --color=auto'

# Terminal Prompt Configuration (Colored for Archanoxy)
PS1='[\[\033[01;32m\]\u\[\033[00m\]@\[\033[01;34m\]\h\[\033[00m\] \W]\$ '

# Enable autocomplete for sudo commands
complete -cf sudo
