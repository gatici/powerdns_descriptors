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
"""PowerDns charm."""

import json
import logging

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus

from powerdns import DomainExceptionError, PowerDns, ZoneExceptionError


class Service:
    """Service Class."""

    def __init__(self, service_info: dict) -> None:
        self._service_info = service_info

    @property
    def ip(self):
        """Get service ip."""
        return self._service_info["ip"][0]

    def get_port(self, port_name):
        """Get port using port name."""
        return self._service_info["ports"][port_name]["port"]


class OsmConfig:
    """OsmConfig Class."""

    def __init__(self, charm: CharmBase) -> None:
        self._charm = charm

    def get_service(self, service_name: str) -> Service:
        """Getting service object using service name."""
        osm_config = json.loads(self._charm.config["osm-config"])
        services = [
            s_values
            for s_name, s_values in osm_config["v0"]["k8s"]["services"].items()
            if service_name in s_name
        ]
        return Service(services[0])


class PowerDnsOperatorCharm(CharmBase):
    """PowerDns Charm."""

    def __init__(self, *args):
        """Constructor for PowerDns Charm."""
        super().__init__(*args)
        self.osm_config = OsmConfig(self)
        self.log = logging.getLogger("powerdns.operator")
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.add_zone_action, self._on_add_zone_action)
        self.framework.observe(self.on.delete_zone_action, self._on_delete_zone_action)

        self.framework.observe(self.on.add_domain_action, self._on_add_domain_action)

        self.framework.observe(self.on.delete_domain_action, self._on_delete_domain_action)

    def _on_config_changed(self, _):
        """Handler for config-changed event."""
        osm_config = self.config.get("osm-config")
        if not osm_config:
            self.unit.status = BlockedStatus("osm-config missing")
            return
        self.log.info(f"osm-config={osm_config}")
        self.unit.status = ActiveStatus()

    def _get_dns_server_instance(self) -> PowerDns:
        powerdns_service = self.osm_config.get_service("webserver-osm-helm-powerdns")
        powerdns_uri = f'http://{powerdns_service.ip}:{powerdns_service.get_port("dns-webserver")}/api/v1/servers/localhost/zones'
        return PowerDns(powerdns_uri)

    def _on_add_zone_action(self, event):
        """Handler for add-zone action."""
        try:
            self.log.info("Running add-zone action...")
            zone = event.params["zone_name"]
            powerdns = self._get_dns_server_instance()
            result = powerdns.add_zone(zone)
            event.set_results({"output": result})
        except ZoneExceptionError as e:
            event.fail(f"Failed to add zone: {e}")

    def _on_delete_zone_action(self, event):
        """Handler for delete-zone action."""
        try:
            self.log.info("Running delete-zone action...")
            zone = event.params["zone_name"]
            powerdns = self._get_dns_server_instance()
            result = powerdns.delete_zone(zone)
            event.set_results({"output": result})
        except ZoneExceptionError as e:
            event.fail(f"Failed to delete zone: {e}")

    def _on_add_domain_action(self, event):
        """Handler for add-domain action."""
        try:
            self.log.info("Running add-domain action...")
            zone = event.params["zone_name"]
            domain = event.params["subdomain"]
            ip = event.params["ip"]
            powerdns = self._get_dns_server_instance()
            result = powerdns.add_domain(zone, domain, ip)
            event.set_results({"output": result})
        except DomainExceptionError as e:
            event.fail(f"Failed to add domain: {e}")

    def _on_delete_domain_action(self, event):
        """Handler for delete domain action."""
        try:
            self.log.info("Running delete-domain action...")
            zone = event.params["zone_name"]
            domain = event.params["subdomain"]
            powerdns = self._get_dns_server_instance()
            result = powerdns.delete_domain(zone, domain)
            event.set_results({"output": result})
        except DomainExceptionError as e:
            event.fail(f"Failed to delete domain: {e}")


if __name__ == "__main__":
    main(PowerDnsOperatorCharm)
