#!/usr/bin/env bash
# shellcheck disable=SC2034

iso_name="archanoxy"
iso_label="ARCH_$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y%m)"
iso_publisher="Archanoxy"
iso_application="Archanoxy Live/Rescue DVD"
iso_version="$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y.%m.%d)"
install_dir="arch"
buildmodes=('iso')
bootmodes=('bios.syslinux'
           'uefi.systemd-boot')
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M' '-Xdict-size' '1M')
bootstrap_tarball_compression=('zstd' '-c' '-T0' '--auto-threads=logical' '--long' '-19')
file_permissions=(
  ["/etc/shadow"]="0:0:400"
  ["/etc/gshadow"]="0:0:400"
  ["/root"]="0:0:750"
  ["/root/.automated_script.sh"]="0:0:755"
  ["/root/.gnupg"]="0:0:700"
  ["/root/.xinitrc"]="0:0:755"
  ["/root/.config/openbox/autostart"]="0:0:755"
  ["/home/liveuser"]="1000:1000:750"
  ["/home/liveuser/.automated_script.sh"]="1000:1000:755"
  ["/home/liveuser/.xinitrc"]="1000:1000:755"
  ["/home/liveuser/.zlogin"]="1000:1000:644"
  ["/home/liveuser/.config"]="1000:1000:755"
  ["/home/liveuser/.config/openbox"]="1000:1000:755"
  ["/home/liveuser/.config/openbox/autostart"]="1000:1000:755"
  ["/etc/skel/.xinitrc"]="0:0:755"
  ["/etc/skel/.config/openbox/autostart"]="0:0:755"
  ["/usr/local/bin/archanoxy-browser"]="0:0:755"
  ["/usr/local/bin/archanoxy-install"]="0:0:755"
  ["/usr/local/bin/choose-mirror"]="0:0:755"
  ["/usr/local/bin/Installation_guide"]="0:0:755"
  ["/usr/local/bin/livecd-sound"]="0:0:755"
  ["/usr/local/bin/fix-pacman"]="0:0:755"
  ["/usr/local/bin/update"]="0:0:755"
  ["/usr/local/bin/net-settings"]="0:0:755"
  ["/usr/local/bin/openbox-manager"]="0:0:755"
)
