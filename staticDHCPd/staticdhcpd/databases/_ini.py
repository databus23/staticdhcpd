# -*- encoding: utf-8 -*-
"""
staticDHCPd module: databases._ini

Purpose
=======
 Provides a uniform datasource API, implementing an INI-file-based backend.
 
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
 
 (C) Neil Tallim, 2013 <flan@uguu.ca>
"""
import ConfigParser
import re

from .. import config

from _generic import Database

class _Config(ConfigParser.RawConfigParser):
    """
    A simple wrapper around RawConfigParser to extend it with support for default values.
    """
    def get(self, section, option, default):
        """
        Returns a custom value, if one is found. Otherwise, returns C{default}.
        
        @type section: basestring
        @param section: The section to be queried.
        @type option: basestring
        @param option: The option to be queried.
        @type default: object
        @param default: The value to be returned, if the requested option is undefined.
        
        @rtype: object
        @return: Either the requested value or the given default.
        """
        try:
            return ConfigParser.RawConfigParser.get(self, section, option)
        except ConfigParser.Error:
            return default
            
    def getint(self, section, option, default):
        """
        Returns a custom value, if one is found. Otherwise, returns C{default}.
        
        @type section: basestring
        @param section: The section to be queried.
        @type option: basestring
        @param option: The option to be queried.
        @type default: int
        @param default: The value to be returned, if the requested option is undefined.
        
        @rtype: int
        @return: Either the requested value or the given default.
        
        @raise ValueError: The value to be returned could not be converted to an C{int}.
        """
        return int(self.get(section, option, default))
        
    def getfloat(self, section, option, default):
        """
        Returns a custom value, if one is found. Otherwise, returns C{default}.
        
        @type section: basestring
        @param section: The section to be queried.
        @type option: basestring
        @param option: The option to be queried.
        @type default: float
        @param default: The value to be returned, if the requested option is undefined.
        
        @rtype: float
        @return: Either the requested value or the given default.
        
        @raise ValueError: The value to be returned could not be converted to a C{float}.
        """
        return float(self.get(section, option, default))
        
    def getboolean(self, section, option, default):
        """
        Returns a custom value, if one is found. Otherwise, returns C{default}.
        
        @type section: basestring
        @param section: The section to be queried.
        @type option: basestring
        @param option: The option to be queried.
        @type default: bool
        @param default: The value to be returned, if the requested option is undefined.
        
        @rtype: bool
        @return: Either the requested value or the given default.
        """
        return bool(str(self.get(section, option, default)).lower().strip() in (
         'y', 'yes',
         't', 'true',
         'ok', 'okay',
         '1',
        ))

class INI(Database):
    """
    Implements an INI broker.
    """
    _maps = None
    _subnets = None
    
    def __init__(self):
        """
        Constructs the broker.
        """
        self._maps = {}
        self._subnets = {}
        self._parse_ini()
        
        self._setupBroker(65536) #Effectively no limit on the number of simultaneous readers
        
    def _parse_ini(self):
        """
        Creates an optimal in-memory representation of the data in the INI file.
        """
        reader = _Config()
        if not reader.read(config.INI_FILE):
            raise ValueError("Unable to read '%(file)s'" % {
             'file': config.INI_FILE,
            })
            
        subnet_re = re.compile(r"^(?P<subnet>.+?)\|(?P<serial>\d+)$")
        mac_re = re.compile(r"^[0-9a-f]{12}$")
        
        for section in reader.sections():
            m = subnet_re.match(section)
            if m:
                self._process_subnet(reader, section, m.group('subnet'), int(m.group('serial')))
            else:
                mac = section.replace(':', '').lower()
                if mac_re.match(mac):
                    self._process_map(reader, section, mac)
                else:
                    pass #Log as unknown entry
                    
        self._validate_references()
        
    def _process_subnet(self, reader, section, subnet, serial):
        lease_time = reader.getint(section, 'lease-time', None)
        if not lease_time:
            raise ValueError("Field 'lease-time' unspecified for '%(section)s'" % {
             'section': section,
            })
        gateway = reader.get(section, 'gateway', None)
        subnet_mask = reader.get(section, 'subnet-mask', None)
        broadcast_address = reader.get(section, 'broadcast-address', None)
        ntp_servers = reader.get(section, 'ntp-servers', None)
        domain_name_servers = reader.get(section, 'domain-name-servers', None)
        domain_name = reader.get(section, 'domain-name', None)
        
        self._subnets[(subnet, serial)] = (
         lease_time,
         gateway, subnet_mask, broadcast_address,
         ntp_servers, domain_name_servers, domain_name
        )
        
    def _process_map(self, reader, section, mac):
        ip = reader.get(section, 'ip', None)
        if not ip:
            raise ValueError("Field 'ip' unspecified for '%(section)s'" % {
             'section': section,
            })
        hostname = reader.get(section, 'hostname', None)
        subnet = reader.get(section, 'subnet', None)
        if not subnet:
            raise ValueError("Field 'subnet' unspecified for '%(section)s'" % {
             'section': section,
            })
        serial = reader.getint(section, 'serial', None)
        if serial is None:
            raise ValueError("Field 'serial' unspecified for '%(section)s'" % {
             'section': section,
            })
        
        mac = ':'.join([mac[0:2], mac[2:4], mac[4:6], mac[6:8], mac[8:10], mac[10:12]])
        self._maps[mac] = (ip, hostname, (subnet, serial))
        
    def _validate_references(self):
        """
        Effectively performs foreign-key checking, to avoid deferred errors.
        """
        for (mac, (_, _, subnet)) in self._maps.items():
            if subnet not in self._subnets:
                raise ValueError("MAC '%(mac)s' references unknown subnet '%(subnet)s|%(serial)i'" % {
                 'mac': mac,
                 'subnet': subnet[0],
                 'serial': subnet[1],
                })
                
    def _lookupMAC(self, mac):
        """
        Queries the database for the given MAC address and returns the IP and
        associated details if the MAC is known.
        
        @type mac: basestring
        @param mac: The MAC address to lookup.
        
        @rtype: tuple(11)|None
        @return: (ip:basestring, hostname:basestring|None,
            gateway:basestring|None, subnet_mask:basestring|None,
            broadcast_address:basestring|None,
            domain_name:basestring|None, domain_name_servers:basestring|None,
            ntp_servers:basestring|None, lease_time:int,
            subnet:basestring, serial:int) or None if no match was
            found.
        
        @raise Exception: If a problem occurs while accessing the database.
        """
        map = self._maps.get(mac)
        if not map:
            return None
            
        (ip, hostname, subnet) = map
        (lease_time,
         gateway, subnet_mask, broadcast_address,
         ntp_servers, domain_name_servers, domain_name
        ) = self._subnets.get(subnet)
        
        return (
         ip, hostname,
         gateway, subnet_mask, broadcast_address,
         domain_name, domain_name_servers, ntp_servers,
         lease_time, subnet[0], subnet[1]
        )
