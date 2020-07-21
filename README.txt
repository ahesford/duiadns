This is a simple dynamic updater for DUIA DNS written in Python.

Dependencies:

  - netaddr >= 0.7.18
    * https://pypi.org/project/netaddr/

  - netifaces >= 0.10.5
    * https://pypi.org/project/netifaces

  - requests 2.7.0
    * https://pypi.org/project/requests/

The updater can optionally update IPv4 or IPv6 addresses for one or more
hostnames using the same MD5 password hash. Parameters are encoded in a simple
INI-style configuration. A commented sample is provided. To invoke the updater,
simply run

	duiadns /path/to/config

This script can be run by a regular user, but running as root (especially
periodically) is recommended to allow permissions on the configuration file to
be restricted to prevent disclosure of the MD5 password hash.

IPv4 addresses are determined from the response of http://ipv4.duiadns.net/.

IPv6 addresses are determined from the response of http://ipv6.duiadns.net/.
The updater will ignore any unreasonable addresses:

* Unspecified (::/128) or link-local (::1/128),
* IPv4 mapping or translation (::ffff:0:0/96, ::ffff:0:0:0/96, 64:ff9b::/96),
* Discard (100::/64)
* Unique local (fc00::/7) and link-local (fe80::/10)

If possible, the updater will also attempt to substitute a stable address
found on the same subnet as the DUIA response if the response corresponds to a
temporary address. (This is currently only possible on BSD or macOS systems.)
