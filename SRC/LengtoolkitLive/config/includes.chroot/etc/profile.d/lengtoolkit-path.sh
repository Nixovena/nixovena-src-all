#!/bin/sh

# LengToolkit PATH adjustment
# Add sbin directories to PATH for all users (critical for rescue tools)
export PATH="$PATH:/usr/local/sbin:/usr/sbin:/sbin"
