# Kali-Live Build-Scripts

_`live-build` configuration for Kali ISO images._

These are the same [build-scripts](https://gitlab.com/kalilinux/build-scripts) that the [Kali team](https://www.kali.org/) uses to generate the official Kali Linux base images, found here: [kali.org/get-kali/](https://www.kali.org/get-kali/).

_Build your Kali Linux image today!_

- - -

These images can be used to live boot into Kali, from such a USB/CD/DVD/sdCard, as well offers a basic installation. For more customization during setup, see [kali-installer](https://gitlab.com/kalilinux/build-scripts/kali-installer).

- [kali-installer](https://gitlab.com/kalilinux/build-scripts/kali-installer) uses [Simple-CDD](https://wiki.debian.org/Simple-CDD) _(which is a wrapper for [debian-cd](https://wiki.debian.org/debian-cd))_
- [kali-live](https://gitlab.com/kalilinux/build-scripts/kali-live) uses [live-build](https://live-team.pages.debian.net/live-manual/html/live-manual/index.en.html)

- - -

Have a look at [Live Build a Custom Kali ISO](https://www.kali.org/docs/development/live-build-a-custom-kali-iso/) for explanations on how to use this repository.

There are also other [code examples of live-build](https://gitlab.com/kalilinux/recipes/live-build-config-examples), as well as [code examples for pre-seed to automate/unattended installation](https://gitlab.com/kalilinux/recipes/kali-preseed-examples).

- - -

## Help

```console
$ ./build.sh --help
Usage: ./build.sh [<option>...]

  --distribution <arg>
  --proposed-updates
  --arch <arg>
  --verbose
  --debug
  --variant <arg>
  --version <arg>
  --subdir <arg>
  --get-image-path
  --no-clean
  --clean
  --help

More information: https://www.kali.org/docs/development/live-build-a-custom-kali-iso/
$
```

## Usage Examples

Both images types, using the latest packages:

```console
$ ./build.sh
[...]
```

- - -

Manually define which Kali mirror to pull from, as well as be more detailed in output:

```console
$ echo "http://kali.download/kali" > .mirror
$
$ ./build.sh --verbose
[...]
```

- - -

Build a different Live image version (GNOME and KDE Plasma):

```console
$ ./build.sh \
  --debug \
  --variant gnome
[...]
$
$ ./build.sh \
  --debug \
  --variant kde
[...]
$
```
