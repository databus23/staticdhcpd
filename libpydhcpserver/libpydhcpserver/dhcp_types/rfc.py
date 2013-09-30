# -*- encoding: utf-8 -*-
"""
libpydhcpserver module: type_rfc

Purpose
=======
 Defines the libpydhcpserver-specific RFC types.
 
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
 
 (C) Neil Tallim, 2010 <red.hamsterx@gmail.com>
"""
try:
    from types import StringTypes
except ImportError: #py3k
    StringTypes = (str,)
    
from conversion import (intToList, longToList)
from ipv4 import IPv4

def rfc3046_decode(l):
    """
    Extracts sub-options from an RFC3046 option (82).
    
    @type l: list
    @param l: The option's raw data.
    
    @rtype: dict
    @return: The sub-options, as byte-lists, keyed by ID.
    """
    sub_options = {}
    while l:
        id = l.pop(0)
        length = l.pop(0)
        sub_options[id] = l[:length]
        l = l[length:]
    return sub_options
    
def rfc3925_decode(l, identifier_size=4):
    """
    Extracts sub-options from an RFC3925 option (124, 125).
    
    identifier_size: the width of the identifier in bytes
    
    * ``vendor_class``: `option 124` as a dictionary of data as strings keyed by
        enterprise numbers
    """
    data = {}
    while option:
        enterprise_number = conversion.listToNumber(option[:identifier_size])
        payload_size = option[identifier_size]
        payload = option[1 + identifier_size:1 + identifier_size + payload_size]
        option = option[1 + identifier_size + payload_size:]
        data[enterprise_number] = payload
    return data
    
def rfc3925_125_decode(l):
    """
    * ``vendor_specific``: `option 125` as a dictionary of data keyed by enterprise
        number; the values are dictionaries that map suboption IDs to data as
        strings
    """
    value = rfc3925_decode(value, identifier_size=4)
    for i in value:
        value[i] = rfc3925_decode(value[i], identifier_size=1)
    return value
    
def _rfc1035Parse(domain_name):
    """
    Splits an FQDN on dots, outputting data like
    ['g', 'o', 'o', 'g', 'l', 'e', 2, 'c', 'a', 0], in conformance with
    RFC1035.
    
    @type domain_name: basestring
    @param domain_name: The FQDN to be converted.
    
    @rtype: list
    @return: The converted FQDN.
    """
    bytes = []
    for fragment in domain_name.split('.'):
        bytes += [len(fragment)] + [ord(c) for c in fragment]
    return bytes + [0]
    
    
class RFC(object):
    """
    A generic special RFC object, used to simplify the process of setting
    complex options.
    """
    _value = None #: The bytes associated with this object.
    
    def getValue(self):
        return self._value
        
    def __hash__(self):
        return self._value.__hash__()
        
    def __repr__(self):
        return repr(self._value)
        
    def __nonzero__(self) :
        return 1
        
    def __cmp__(self, other):
        if isinstance(other, RFC):
            return cmp(self._value, other.getValue())
        return cmp(self._value, other)
        
class rfc1035_plus(RFC):
    def __init__(self, data):
        """
        Parses the given data and stores multiple RFC1035-formatted strings.
        
        @type data: basestring
        @param data: The comma-delimited FQDNs to process.
        """
        self._value = []
        for token in [tok for tok in [t.strip() for t in data.split(',')] if tok]:
            self._value += _rfc1035Parse(token)
            
class rfc2610_78(RFC):
    def __init__(self, mandatory, data):
        """
        Parses the given data and stores multiple IPv4 addresses.
        
        @type mandatory: bool
        @param mandatory: True if the IPv4 addresses have to be respected.
        @type data: basestring
        @param data: The comma-delimited IPv4s to process.
        """
        self._value = [int(mandatory)]
        for token in [tok for tok in [t.strip() for t in data.split(',')] if tok]:
            self._value += IPv4(token)

class rfc2610_79(RFC):
    def __init__(self, mandatory, data):
        """
        Parses the given data and stores a scope-list.
        
        @type mandatory: bool
        @param mandatory: True if the scope-list has to be respected.
        @type data: basestring
        @param data: The scope-list to process.
        """
        self._value = [int(mandatory)] + [ord(c) for c in data.encode('utf-8')]

class rfc3361_120(RFC):
    def __init__(self, data):
        """
        Parses the given data and stores multiple IPv4 addresses or
        RFC1035-formatted strings.
        
        @type data: basestring
        @param data: The comma-delimited IPv4s or FQDNs to process.
        
        @raise ValueError: Both IPv4s and FQDNs were specified.
        """
        ip_4_mode = False
        dns_mode = False
        
        self._value = []
        for token in [tok for tok in [t.strip() for t in data.split(',')] if tok]:
            try:
                self._value += IPv4(token)
                ip_4_mode = True
            except ValueError:
                self._value += _rfc1035Parse(token)
                dns_mode = True
                
        if ip_4_mode == dns_mode:
            raise ValueError("'%(data)s contains both IPv4 and DNS-based entries" % {
             'data': data,
            })
            
        self._value.insert(0, int(ip_4_mode))

class rfc3397_119(rfc1035_plus): pass

class rfc3925_124(RFC):
    def __init__(self, data):
        """
        Sets vendor_class data.

        @type data: list
        @param data: A list of the form [(enterprise_number:int, data:string)].
        """
        self._value = []
        for (enterprise_number, payload) in data:
            self._value += longToList(enterprise_number)
            self._value.append(chr(len(payload)))
            self._value += payload

class rfc3925_125(RFC):
    def __init__(self, data):
        """
        Sets vendor_specific data.

        @type data: list
        @param data: A list of the form
            [(enterprise_number:int, [(subopt_code:byte, data:string)])].
        """
        self._value = []
        for (enterprise_number, payload) in data:
            self._value += longToList(enterprise_number)
            
            subdata = []
            for (subopt_code, subpayload) in payload:
                subdata.append(chr(subopt_code))
                subdata.append(chr(len(subpayload)))
                subdata += subpayload
                
            self._value.append(chr(len(subdata)))
            self._value += subdata

class rfc4174_83(RFC):
    def __init__(self, isns_functions, dd_access, admin_flags, isns_security, ips):
        """
        Sets iSNS configuration parameters.
        
        @type isns_functions: int
        @param isns_functions: Two bytes.
        @type dd_access: int
        @param dd_access: Two bytes.
        @type admin_flags: int
        @param admin_flags: Two bytes.
        @type isns_security: int
        @param isns_security: Four bytes.
        @type ips: basestring
        @param ips: The comma-delimited IPv4s to process.
        """
        isns_functions = intToList(isns_functions)
        dd_access = intToList(dd_access)
        admin_flags = intToList(admin_flags)
        isns_security = longToList(isns_security)
        
        self._value = isns_functions + dd_access + admin_flags + isns_security
        for token in [tok for tok in [t.strip() for t in ips.split(',')] if tok]:
            self._value += IPv4(token)

class rfc4280_88(rfc1035_plus): pass

class rfc5223_137(rfc1035_plus): pass

class rfc5678_139(RFC):
    def __init__(self, values):
        """
        Parses the given data and stores multiple IPv4 addresses
        associated with sub-option codes.
        
        @type values: tuple
        @param values: A collection of (code:int, IPv4s:string) elements.
        """
        self._value = []
        for (code, addresses) in values:
            self._value.append(code)
            for token in [tok for tok in [address.strip() for address in addresses.split(',')] if tok]:
                self._value += IPv4(token)

class rfc5678_140(RFC):
    def __init__(self, values):
        """
        Parses the given data and stores multiple RFC1035-formatted strings
        associated with sub-option codes.
        
        @type values: tuple
        @param values: A collection of (code:int, FQDNs:string) elements.
        """
        self._value = []
        for (code, addresses) in values:
            self._value.append(code)
            self._value += rfc1035_plus(addresses).getValue()
