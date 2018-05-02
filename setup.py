#!/usr/bin/env python
'''
duiadns.py: A Python client for DUIA dynamic DNS updates

The duiadns.py script is maintained by Andrew J. Hesford to update IPv4 and
IPv6 addresses in the DUIA dynamic DNS system. Unlike the service-provided
client, duiadns.py is aware of temporary IPv6 addresses and attempts to
identify the underlying permanent address when updating.
'''

# Copyright (c) 2015--2018 Andrew J. Hesford. All rights reserved.
# Restrictions are listed in the LICENSE file distributed with this package.

DOCLINES = __doc__.split('\n')
VERSION = '1.1'

if __name__ == '__main__':
	from setuptools import setup

	setup(name='duiadns',
			version=VERSION,
			description=DOCLINES[0],
			long_description='\n'.join(DOCLINES[2:]),
			author='Andrew J. Hesford',
			author_email='ajh@sideband.org',
			platforms=['any'], license='BSD',
			scripts=['duiadns.py',],
			install_requires=[
				'netifaces',
				'netaddr',
				'requests'
			],
		)
