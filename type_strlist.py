# -*- encoding: utf-8 -*-
"""
libpydhcpserver module: type_strlist

Purpose
=======
 Defines the libpydhcpserver-specific strlist type.
 
Legal
=====
 This file is part of libpydhcpserver.
 libpydhcpserver is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program. If not, see <http://www.gnu.org/licenses/>.
 
 (C) Neil Tallim, 2010 <flan@uguu.ca>
 (C) Mathieu Ignacio, 2008 <mignacio@april.org>
"""
class strlist(object):
	def __init__(self, data=""):
		str_type = type(data)
		if str_type == str:
			self._str = data
			self._list = map(ord, self._str)
		elif str_type in (list, tuple):
			self._list = data
			self._str = "".join(map(chr, self._list))
		else:
			raise TypeError('strlist init : expected str or [int]; got %(type)s' % {'type': str_type,})
			
	# return string
	def str(self):
		return self._str
		
	# return list (useful for DhcpPacket class)
	def list(self):
		return self._list
		
	# return int
	def int(self):
		return 0
		
	def __hash__(self):
		return self._str.__hash__()
		
	def __repr__(self):
		return self._str
		
	def __nonzero__(self) :
		if self._str:
			return 1
		return 0
		
	def __cmp__(self, other):
		if self._str == other:
			return 0
		return 1
		