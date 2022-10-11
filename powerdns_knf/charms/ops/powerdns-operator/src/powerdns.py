#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact: legal@canonical.com
#
# To get in touch with the maintainers, please contact:
# osm-charmers@lists.launchpad.net
#
# Learn more about testing at: https://juju.is/docs/sdk/testing
"""DNS server."""

import json
import logging

import requests

APIKEY = "pdnsapikey"


class ZoneExceptionError(Exception):
    """DNS Zone Exception Class."""


class DomainExceptionError(Exception):
    """DNS Domain Exception Class."""


class PowerDns:
    """PowerDns Class."""

    def __init__(self, powerdns_uri: str) -> None:
        """Powerdns Constructor.

        Args:
            powerdns_uri    (str):  powerdns url to send the request
        """
        self.url = powerdns_uri
        self.headers = {"X-API-Key": APIKEY}
        self.log = logging.getLogger("powerdns")

    def add_zone(self, zone: str) -> str:
        """Add Zone to DNS Server.

        Args:
            zone    (str):  zone to be registered

        Returns:
            status code:request output  (str)

        Raises:
            ZoneException
        """
        payload = {
            "name": zone,
            "kind": "Native",
            "masters": [],
            "nameservers": [f"nameserver.{zone}"],
        }
        r = requests.post(url=self.url, data=json.dumps(payload), headers=self.headers)

        if r.status_code != 201:
            err_code = str(r.status_code)
            self.log.error(err_code + " " + r.text)
            raise ZoneExceptionError(
                f"Add zone operation failed with status code {err_code}, {r.text}"
            )
        else:
            self.log.info("Added zone {zone}")
            return f"{r.status_code}:{r.text}"

    def delete_zone(self, zone: str) -> str:
        """Delete Zone from DNS Server.

        Args:
            zone    (str):  zone to be deleted

        Returns:
            status code:request output  (str)

        Raises:
            ZoneException
        """
        r = requests.delete(url=self.url + "/" + zone, headers=self.headers)
        if r.status_code != 204:
            err_code = str(r.status_code)
            self.log.error(err_code + " " + r.text)
            raise ZoneExceptionError(
                f"Delete zone operation failed with status code {err_code}, {r.text}"
            )
        else:
            self.log.info(f"Deleted zone {zone}")
            return f"{r.status_code}:{r.text}"

    def add_domain(self, zone: str, domain: str, ip: str) -> str:
        """Add Domain to DNS Server.

        Args:
            zone    (str):  zone of domain
            domain  (str):  domain to be registered
            ip  (str):      ip address for domain

        Returns:
            status code:request output  (str)

        Raises:
            DomainException
        """
        payload = {
            "rrsets": [
                {
                    "name": domain + zone,
                    "type": "A",
                    "ttl": 86400,
                    "changetype": "REPLACE",
                    "records": [{"content": ip}],
                }
            ]
        }

        r = requests.patch(
            url=self.url + "/" + zone, data=json.dumps(payload), headers=self.headers
        )
        if r.status_code != 204:
            err_code = str(r.status_code)
            self.log.error(err_code + " " + r.text)
            raise DomainExceptionError(
                f"Add domain operation failed with status code {err_code}, {r.text}"
            )
        else:
            self.log.info(f"Added record of {domain}{zone} in {ip}")
            return f"{r.status_code}:{r.text}"

    def delete_domain(self, zone: str, domain: str) -> str:
        """Delete Domain from DNS Server.

        Args:
            zone    (str):  zone of domain
            domain  (str):  domain to be deleted

        Returns:
            status code:request output  (str)

        Raises:
            DomainException
        """
        payload = {"rrsets": [{"name": domain + zone, "type": "A", "changetype": "DELETE"}]}

        r = requests.patch(self.url + "/" + zone, data=json.dumps(payload), headers=self.headers)
        if r.status_code != 204:
            err_code = str(r.status_code)
            self.log.error(err_code + " " + r.text)
            raise DomainExceptionError(
                f"Delete domain operation failed with status code {err_code}, {r.text}"
            )
        else:
            self.log.info(f"Deleted record of {domain} in zone {zone}")
            return f"{r.status_code}:{r.text}"
