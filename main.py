# -*- encoding: utf-8 -*-
"""
staticDHCPd module: main

Purpose
=======
 Runs a staticDHCPd server.
 
Legal
=====
 All code, unless otherwise indicated, is original, and subject to the terms of
 the GNU General Public License version 3, which is provided in COPYING.
 
 (C) Neil Tallim, 2009
"""
import sys
import time

import conf

import src.dhcp
import src.web

if __name__ == '__main__':
	dhcp_thread = src.dhcp.DHCPService()
	dhcp_thread.start()
	
	web_thread = src.web.WebService()
	web_thread.start()
	
	while True:
		time.sleep(conf.POLLING_INTERVAL)
		dhcp_thread.getStats()
		