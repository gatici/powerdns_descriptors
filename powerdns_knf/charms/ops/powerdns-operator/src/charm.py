#!/usr/bin/env python3
# Copyright 2022
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

import json
import logging

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus

import requests


logger = logging.getLogger(__name__)

APIKEY = "pdnsapikey"


class ZoneException(Exception):
    pass


class DomainException(Exception):
    pass


class Service:
    def __init__(self, service_info):
        self._service_info = service_info

    @property
    def ip(self):
        return self._service_info["ip"][0]

    def get_port(self, port_name):
        return self._service_info["ports"][port_name]["port"]


class OsmConfig:
    def __init__(self, charm: CharmBase) -> None:
        self._charm = charm

    def get_service(self, service_name: str) -> Service:
        osm_config = json.loads(self._charm.config["osm-config"])
        services = [
            s_values
            for s_name, s_values in osm_config["v0"]["k8s"]["services"].items()
            if service_name in s_name
        ]
        return Service(services[0])


class PowerDns:
    def __init__(self, powerdns_uri: str) -> None:
        self.url = powerdns_uri
        self.headers = {"X-API-Key": APIKEY}
        self.log = logging.getLogger("powerdns")

    def add_zone(self, zone):
        payload = {
            "name": zone,
            "kind": "Native",
            "masters": [],
            "nameservers": [f"nameserver.{zone}"],
        }
        r = requests.post(url=self.url, data=json.dumps(payload), headers=self.headers)
        if r.status_code != 201:
            err_code = f"{r.status_code}"
            self.log.error(err_code, r.text)
            raise ZoneException(f"Add zone operation failed with status code {err_code}, {r.text}")
        else:
            self.log.info("Added zone {zone}")
            return f"{r.status_code}:{r.text}"

    def delete_zone(self, zone):
        r = requests.delete(url=self.url + "/" + zone, headers=self.headers)
        if r.status_code != 204:
            err_code = f"{r.status_code}"
            self.log.error(err_code, r.text)
            raise ZoneException(f"Delete zone operation failed with status code {err_code}, {r.text}")
        else:
            self.log.info(f"Deleted zone {zone}")
            return f"{r.status_code}:{r.text}"

    def add_domain(self, zone, domain, ip):
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
            err_code = f"{r.status_code}"
            self.log.error(err_code, r.text)
            raise DomainException(f"Add domain operation failed with status code {err_code}, {r.text}")
        else:
            self.log.info(f"Added record of {domain}{zone} in {ip}")
            return f"{r.status_code}:{r.text}"

    def delete_domain(self, zone, domain):
        payload = {
            "rrsets": [{"name": domain + zone, "type": "A", "changetype": "DELETE"}]
        }

        r = requests.patch(
            self.url + "/" + zone, data=json.dumps(payload), headers=self.headers
        )
        if r.status_code != 204:
            err_code = f"{r.status_code}"
            self.log.error(err_code, r.text)
            raise DomainException(f"Delete domain operation failed with status code {err_code}, {r.text}")
        else:
            self.log.info(f"Deleted record of {domain} in zone {zone}")
            return f"{r.status_code}:{r.text}"


class PowerDnsOperatorCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)
        self.osm_config = OsmConfig(self)
        self.log = logging.getLogger("powerdns.operator")
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(
            self.on.add_zone_action, self._on_add_zone_action
        )
        self.framework.observe(
            self.on.delete_zone_action, self._on_delete_zone_action
        )

        self.framework.observe(
            self.on.add_domain_action, self._on_add_domain_action
        )

        self.framework.observe(
            self.on.delete_domain_action, self._on_delete_domain_action
        )

    def _on_config_changed(self, _):
        """Handler for config-changed event."""
        osm_config = self.config.get("osm-config")
        if not osm_config:
            self.unit.status = BlockedStatus("osm-config missing")
            return
        logger.info(f"osm-config={osm_config}")
        self.unit.status = ActiveStatus()

    def _get_dns_server_instance(self, service_name):
        powerdns_service = self.osm_config.get_service(service_name)
        powerdns_uri = f'http://{powerdns_service.ip}:8081/api/v1/servers/localhost/zones'
        return PowerDns(powerdns_uri)

    def _on_add_zone_action(self, event):
        """Handler for add-zone action."""
        try:
            self.log.info("Running add-zone action...")
            service_name = event.params["service_name"]
            zone = event.params["zone_name"]
            powerdns = self._get_dns_server_instance(service_name)
            result = powerdns.add_zone(zone)
            event.set_results({"output": result})
        except ZoneException as e:
            event.fail(f"Failed to add zone: {e}")

    def _on_delete_zone_action(self, event):
        """Handler for delete-zone action."""
        try:
            self.log.info("Running delete-zone action...")
            service_name = event.params["service_name"]
            zone = event.params["zone_name"]
            powerdns = self._get_dns_server_instance(service_name)
            result = powerdns.delete_zone(zone)
            event.set_results({"output": result})
        except ZoneException as e:
            event.fail(f"Failed to delete zone: {e}")

    def _on_add_domain_action(self, event):
        """Handler for add-domain action."""
        try:
            self.log.info("Running add-domain action...")
            service_name = event.params["service_name"]
            zone = event.params["zone_name"]
            domain = event.params["subdomain"]
            ip = event.params["ip"]
            powerdns = self._get_dns_server_instance(service_name)
            result = powerdns.add_domain(zone, domain, ip)
            event.set_results({"output": result})
        except ZoneException as e:
            event.fail(f"Failed to add domain: {e}")


    def _on_delete_domain_action(self, event):
        """Handler for delete domain action."""
        try:
            self.log.info("Running delete-domain action...")
            service_name = event.params["service_name"]
            zone = event.params["zone_name"]
            domain = event.params["subdomain"]
            powerdns = self._get_dns_server_instance(service_name)
            result = powerdns.delete_domain(zone, domain)
            event.set_results({"output": result})
        except ZoneException as e:
            event.fail(f"Failed to delete domain: {e}")


if __name__ == "__main__":
    main(PowerDnsOperatorCharm)
