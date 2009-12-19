# -*- encoding: utf-8 -*-
"""
staticDHCPd module: src.web

Purpose
=======
 Provides a web interface for viewing and interacting with a staticDHCPd server.
 
Legal
=====
 This file is part of staticDHCPd.
 staticDHCPd is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program. If not, see <http://www.gnu.org/licenses/>.
 
 (C) Neil Tallim, 2009
"""
import BaseHTTPServer
import cgi
import hashlib
import os
import select
import threading
import time
import urlparse

import conf

import src.logging

class _WebServer(BaseHTTPServer.BaseHTTPRequestHandler):
	"""
	The handler that responds to all received HTTP requests.
	"""
	_allowed_pages = ('/', '/index.html') #: A collection of all paths that will be allowed.
	
	def do_GET(self):
		if not self.path in self._allowed_pages:
			self.send_response(404)
			return
		self._doResponse()
		
	def do_HEAD(self):
		if not self.path in self._allowed_pages:
				self.send_response(404)
				return
				
		try:
			self.send_response(200)
			self.send_header('Content-type', 'text/html')
			self.send_header('Last-modified', time.strftime('%a, %d %b %Y %H:%M:%S %Z'))
			self.end_headers()
		except Exception, e:
			src.logging.writeLog("Problem while processing HEAD in Web module: %(errors)s" % {'error': str(e),})
			
	def do_POST(self):
		try:
			(ctype, pdict) = cgi.parse_header(self.headers.getheader('content-type'))
			if ctype == 'application/x-www-form-urlencoded':
				query = urlparse.parse_qs(self.rfile.read(int(self.headers.getheader('content-length'))))
				key = query.get('key')
				if key:
					if hashlib.md5(key[0]).hexdigest() == conf.WEB_RELOAD_KEY:
						if src.logging.logToDisk():
							src.logging.writeLog("Wrote log to '%(log)s'" % {'log': conf.LOG_FILE,})
						else:
							src.logging.writeLog("Unable to write log to '%(log)s'" % {'log': conf.LOG_FILE,})
					else:
						src.logging.writeLog("Invalid Web-access-key provided")
		except Exception, e:
			src.logging.writeLog("Problem while processing POST in Web module: %(errors)s" % {'error': str(e),})
		self._doResponse()
		
	def _doResponse(self):
		try:
			self.send_response(200)
			self.send_header('Content-type', 'text/html')
			self.send_header('Last-modified', time.strftime('%a, %d %b %Y %H:%M:%S %Z'))
			self.end_headers()
			
			self.wfile.write('<html><head><title>staticDHCPd log</title></head><body>')
			self.wfile.write('<div style="width: 950px; margin-left: auto; margin-right: auto; border: 1px solid black;">')
			
			self.wfile.write('<div>Statistics:<div style="text-size: 0.9em; margin-left: 20px;">')
			for (timestamp, packets, discarded, time_taken, ignored_macs) in src.logging.readPollRecords():
				if packets:
					turnaround = time_taken / packets
				else:
					turnaround = 0.0
				self.wfile.write("%(time)s : processed: %(processed)i; discarded: %(discarded)i; turnaround: %(turnaround)fs/pkt; ignored MACs: %(ignored)i<br/>" % {
				 'time': time.ctime(timestamp),
				 'processed': packets,
				 'discarded': discarded,
				 'turnaround': turnaround,
				 'ignored': ignored_macs,
				})
			self.wfile.write("</div></div><br/>")
			
			self.wfile.write('<div>Events:<div style="text-size: 0.9em; margin-left: 20px;">')
			for (timestamp, line) in src.logging.readLog():
				self.wfile.write("%(time)s : %(line)s<br/>" % {
				 'time': time.ctime(timestamp),
				 'line': cgi.escape(line),
				})
			self.wfile.write("</div></div><br/>")
			
			self.wfile.write('<div style="text-align: center;">')
			self.wfile.write('<small>Summary generated %(time)s</small><br/>' % {
			 'time': time.asctime(),
			})
			self.wfile.write('<small>PID: %(pid)i | Server: %(server)s:%(port)i</small><br/>' % {
			 'pid': os.getpid(),
			 'server': conf.DHCP_SERVER_IP,
			 'port': conf.DHCP_SERVER_PORT,
			})
			self.wfile.write('<form action="/" method="post"><div style="display: inline;">')
			self.wfile.write('<label for="key">Key: </label><input type="password" name="key" id="key"/>')
			self.wfile.write('<input type="submit" value="Write log to disk"/>')
			self.wfile.write('</div></form>')
			self.wfile.write('</div>')
			
			self.wfile.write("</div></body></html>")
			
			return
		except Exception, e:
			src.logging.writeLog("Problem while serving response in Web module: %(errors)s" % {'error': str(e),})
			
			
class WebService(threading.Thread):
	"""
	A thread that handles HTTP requests indefinitely, daemonically.
	"""
	_web_server = None #: The handler that responds to HTTP requests.
	
	def __init__(self):
		"""
		Sets up the Web server.
		"""
		threading.Thread.__init__(self)
		self.daemon = True
		
		self._web_server = BaseHTTPServer.HTTPServer(
		 (conf.WEB_IP, conf.WEB_PORT), _WebServer
		)
		
		src.logging.writeLog('Configured Web server')
		
	def run(self):
		"""
		Runs the Web server indefinitely.
		
		In the event of an unexpected error, e-mail will be sent and processing
		will continue with the next request.
		"""
		src.logging.writeLog('Running Web server')
		while True:
			try:
				self._web_server.handle_request()
			except select.error:
				src.logging.writeLog('Suppressed non-fatal select() error in Web module')
			except Exception, e:
				src.logging.sendErrorReport('Unhandled exception', e)
				