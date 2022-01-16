import logging
import socket

from dataclasses import dataclass
from pprint import pprint

import whois


from aws_log_parser.plugin import AwsLogParserPlugin
from aws_log_parser.util import gethostbyname

logger = logging.getLogger(__name__)


@dataclass
class RadbPlugin(AwsLogParserPlugin):
    attr_name: str = "network"

    def parse_response(self, response):
        pprint(response)

        d = {}
        for line in response.split("\n"):
            if line == "":
                break
            if ":" not in line:
                continue
            s = line.split(":", 1)
            d[s[0].strip()] = s[1].strip()
        return d

    def _query(self, ip_address):
        try:
            response = whois.NICClient().whois(
                ip_address,
                gethostbyname("whois.radb.net"),
                0,
            )
        except (
            socket.gaierror,
            socket.herror,
            socket.timeout,
            ConnectionResetError,
        ) as exc:
            logger.error(f"{ip_address} lookup failed: {str(exc)}")
        else:
            self._cache.update({ip_address: self.parse_response(response).get("descr")})

    def query(self, ip_addresses):
        for ip_address in ip_addresses:
            self._query(ip_address)

    def augment(self, log_entries):

        networks = self.lookup({log_entry.client_ip for log_entry in log_entries})

        pprint(networks)

        for log_entry in log_entries:
            setattr(log_entry, self.attr_name, networks.get(log_entry.client_ip))
            yield log_entry