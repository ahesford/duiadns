#!/usr/bin/env python

import sys
import requests
import netifaces
import ConfigParser

_useragent = "DUIA-DNS-UPDATER/1.0"

def addrweb(v4=True):
	'''
	Returns the address (IPv4 if v4 is True, IPv6 otherwise) as seen by the
	DUIA web server. If an address is not available, returns None.

	This method consumes all connection and IP formatting errors.
	'''
	from netaddr import IPAddress, INET_PTON
	ipurl = "http://%s.duia.ro" % ("ipv4" if v4 else "ipv6")
	try: r = requests.get(ipurl, headers={'User-Agent': _useragent})
	except: return None

	# Convert the response to an address if possible
	try: addr = IPAddress(r.text, version=(4 if v4 else 6), flags=INET_PTON)
	except: return None

	return str(addr)


def findipv6():
	'''
	Use the public (and perhaps temporary) IPv6 address seen by DUIA to
	select a non-temporary and non-link-local address on the same
	interface. If the DUIA-identified address is neither temporary nor
	deprecated, it is always returned. Otherwise, the first suitable
	address is returned.

	If no matching address can be found, None is returned.
	'''
	from netaddr import IPAddress, IPNetwork

	# Find the address identified by DUIA, if possible
	try: pubaddr = IPAddress(addrweb(v4=False))
	except: return None

	def validate_ipv6(addr):
		'''
		Convert an addr dictionary produced by netifaces into an
		(IPAddress, bool) tuple where the bool is True if and only if
		addr does not contain 'temporary' or 'deprecated' flags and is
		not link-local or loopback.
		'''
		# Canonize the address
		ipaddr = IPAddress(addr['addr'])

		# Ensure the address is not link-local or loopback
		if ipaddr in IPNetwork('fe80::/10') or ipaddr == IPAddress('::1'):
			return ipaddr, False

		# If no flags are present, assume the address is valid
		try: flags = addr['flags']
		except KeyError: return ipaddr, True

		# These values are defined on OS X
		tempflag, deprflag = 0x0080, 0x0010
		return ipaddr, not (flags & tempflag or flags & deprflag)


	# Loop through all interfaces to find possible addresses
	for iface in netifaces.interfaces():
		# Try to grab any IPv6 addresses available for this interface
		try: addrs = netifaces.ifaddresses(iface)[netifaces.AF_INET6]
		except KeyError: continue

		# Build an IPAddress -> flags map
		addrmap = dict(validate_ipv6(addr) for addr in addrs)

		# If the public address is not on this interface, move on
		if pubaddr not in addrmap: continue

		# If the public address is valid, prefer it
		if addrmap[pubaddr]: return str(pubaddr)

		# Otherwise, just return the first valid address
		for addr, valid in addrmap.iteritems():
			if valid: return str(addr)

		# No need to look over other interfaces
		break

	return None


def findipv4():
	'''
	Use a DUIA service to determine the public IP address of this machine.
	'''
	return addrweb(v4=True)


def postupdate(host, md5pass, ipv4=None, ipv6=None):
	'''
	Post an update of the specified host with the provided IPv4 and IPv6
	addresses. Either can be None to skip an update of the corresponding
	record.

	Returns True on success, False otherwise
	'''
	if not (ipv4 or ipv6):
		raise ValueError('At least one of ipv4 and ipv6 must be specified')

	# Build the update URL
	srv = ("http://ipv%d.duia.ro/dynamic.duia?host=%s&password=%s" %
			((6 if not ipv4 else 4), host, md5pass))
	if ipv4: srv += "&ip4=" + ipv4
	if ipv6: srv += "&ip6=" + ipv6

	# Try to perform the update
	try: r = requests.get(srv, headers={'User-Agent': _useragent})
	except: return False

	return r.status_code == 200


def readcache(cache):
	'''
	Attempt to read the specified cache file as a JSON object, or else
	return an empty dictionary.

	The expected format has hostnames as keys and dictionaries as values,
	where the value dictionary has optional 'ipv4' and 'ipv6' keys with
	string values representing corresponding addresses.
	'''
	import json
	try:
		f = open(cache, 'r')
	except IOError:
		return {}

	cmap = json.load(f)
	return cmap


def writecache(cmap, cache):
	'''
	Attempt to store the cmap dictionary in the location specified by cache.
	'''
	import json
	f = open(cache, 'w')
	json.dump(cmap, f)
	f.write('\n')
	f.close()


def getaddrupdate(newaddr, cache):
	'''
	If newaddr is None or an invalid IP address, return None; if newaddr
	and cache are both equivalent IP addresses, return None; otherwise,
	return newaddr.
	'''
	from netaddr import IPAddress, AddrFormatError

	try: newaddr = IPAddress(newaddr)
	except AddrFormatError: return None

	try: cache = IPAddress(cache)
	except AddrFormatError: return str(newaddr)

	if newaddr == cache: return None
	return str(newaddr)


def updateEngine(config):
	'''
	Process a ConfigParser and perform a DNS update accordingly.
	'''
	dsec = 'duia'

	try:
		hostnames = config.get(dsec, 'hostname').split()
	except ConfigParser.Error:
		print >> sys.stderr, 'ERROR: Configuration must specify at least one hostname in [%s]' % dsec
		return False

	try:
		password = config.get(dsec, 'password')
	except ConfigParser.Error:
		print >> sys.stderr, 'ERROR: Configuration must specify password in [%s]' % dsec
		return False

	try:
		cache = config.get(dsec, 'cache')
	except ConfigParser.Error:
		print >> sys.stderr, 'ERROR: Configuration must specify cache in [%s]' % dsec
		return False

	try:
		usev4 = config.getboolean(dsec, 'ipv4')
	except ConfigParser.NoOptionError:
		usev4 = False
	except ConfigParser.Error:
		print >> sys.stderr, 'ERROR: Optional ipv4 boolean in [%s] incorrectly specified' % dsec
		return False

	try:
		usev6 = config.getboolean(dsec, 'ipv6')
	except ConfigParser.NoOptionError:
		usev6 = False
	except ConfigParser.Error:
		print >> sys.stderr, 'ERROR: Optional ipv6 boolean in [%s] incorrectly specified' % dsec
		return False

	if not (usev4 or usev6):
		print >> sys.stderr, 'ERROR: At least one of ipv4 and ipv6 booleans in [%s] must be true' % dsec
		return False

	try: cachemap = readcache(cache)
	except ValueError:
		print >> sys.stderr, 'ERROR: Cache file %s exists but could not be parsed' % cache
		return False

	from netaddr import IPAddress

	for hostname in hostnames:
		crec = cachemap.get(hostname, {})

		# Determine if the IPv4 and IPv6 addresses need updating
		if usev4:
			addr4 = getaddrupdate(findipv4(), crec.get('ipv4', None))
		else: addr4 = None
		if usev6:
			addr6 = getaddrupdate(findipv6(), crec.get('ipv6', None))
		else: addr6 = None

		if not addr4 and not addr6:
			print 'Update unnecessary for', hostname
			continue

		# Attempt an (atomic?) update
		postresult = postupdate(hostname, password, addr4, addr6)
		if postresult:
			print 'Successful update for', hostname, (addr4 or ''), (addr6 or '')
			if addr4: crec['ipv4'] = addr4
			if addr6: crec['ipv6'] = addr6
			cachemap[hostname] = crec
		else:
			print 'Update failed for', hostname, (addr4 or ''), (addr6 or '')

	try: writecache(cachemap, cache)
	except IOError:
		print >> sys.stderr, 'ERROR: Could not store IP cache at location', cache
		return False

	return True


if __name__ == '__main__':
	if len(sys.argv) != 2:
		print >> sys.stderr, "USAGE: %s <configuration>" % sys.argv[0]
		sys.exit(1)

	# Read the configuration file
	try:
		f = open(sys.argv[1])
		config = ConfigParser.SafeConfigParser()
		config.readfp(f)
	except Exception as e:
		print >> sys.stderr, "ERROR: Unable to process configuration %s" % sys.argv[1]
		sys.exit(1)

	if not updateEngine(config): sys.exit(1)
