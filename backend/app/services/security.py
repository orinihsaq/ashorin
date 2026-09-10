import ipaddress
import socket
from urllib.parse import urlparse
from app.utils.errors import SSRFSecurityError, ValidationError
from app.utils.logger import logger


# Specific blocked hostnames (cloud metadata, internal aliases)
BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata",
    "instance-data",
}

# Specific blocked IPv4/IPv6 networks
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network (only valid as source)
    ipaddress.ip_network("10.0.0.0/8"),         # Private-Use (RFC 1918)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-Local / Cloud Metadata (169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),      # Private-Use (RFC 1918)
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # Documentation (TEST-NET-1)
    ipaddress.ip_network("192.168.0.0/16"),     # Private-Use (RFC 1918)
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),    # Documentation (TEST-NET-2)
    ipaddress.ip_network("203.0.113.0/24"),     # Documentation (TEST-NET-3)
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    # IPv6 blocked
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("::ffff:0:0/96"),      # IPv4-mapped
    ipaddress.ip_network("100::/64"),           # Discard-Only
    ipaddress.ip_network("2001:db8::/32"),      # Documentation
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-Local Unicast
    ipaddress.ip_network("ff00::/8"),           # Multicast
]


class SecurityService:
    @staticmethod
    def validate_url(url: str) -> str:
        """
        Validates URL scheme and protects against SSRF attacks.
        Returns the sanitized URL string if valid.
        Raises ValidationError or SSRFSecurityError if invalid or blocked.
        """
        if not url or not isinstance(url, str):
            raise ValidationError("Please enter a valid HTTP or HTTPS URL.")

        url = url.strip()

        # Disallow newlines and control characters
        if any(c in url for c in ['\r', '\n', '\t', '\0']):
            raise ValidationError("URL contains invalid control characters.")

        try:
            parsed = urlparse(url)
        except Exception:
            raise ValidationError("Please enter a valid HTTP or HTTPS URL.")

        # Scheme check: only http and https are permitted
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValidationError("Only HTTP and HTTPS URLs are supported.")

        hostname = parsed.hostname
        if not hostname:
            raise ValidationError("URL must contain a valid domain name or host.")

        hostname = hostname.lower().strip(".")

        # Check blocked hostnames
        if hostname in BLOCKED_HOSTNAMES or hostname.endswith(".local") or hostname.endswith(".internal"):
            logger.warning(f"SSRF block: disallowed hostname '{hostname}'")
            raise SSRFSecurityError("Access to local or private network addresses is restricted.")

        # Check if the hostname is a direct IP address
        try:
            ip = ipaddress.ip_address(hostname)
            SecurityService._validate_ip_address(ip)
            return url
        except ValueError:
            # Not a raw IP literal; proceed with DNS resolution
            pass

        # Resolve DNS to verify all destination IPs
        try:
            # Resolve both IPv4 and IPv6
            addr_info = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
            if not addr_info:
                raise ValidationError(f"Could not resolve host: {hostname}")

            for entry in addr_info:
                sockaddr = entry[4]
                ip_str = sockaddr[0]
                ip = ipaddress.ip_address(ip_str)
                SecurityService._validate_ip_address(ip)

        except socket.gaierror as e:
            logger.warning(f"DNS resolution failure for host '{hostname}': {e}")
            raise ValidationError("The remote website could not be reached. Please check the URL.")
        except SSRFSecurityError:
            raise
        except Exception as e:
            logger.warning(f"Unexpected error validating URL host '{hostname}': {e}")
            raise ValidationError("Could not validate target URL.")

        return url

    @staticmethod
    def _validate_ip_address(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
        """Ensure IP address does not belong to any forbidden or private range."""
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            logger.warning(f"SSRF block: IP {ip} is private/loopback/restricted")
            raise SSRFSecurityError("Access to local or private network addresses is restricted.")

        for net in BLOCKED_NETWORKS:
            if ip in net:
                logger.warning(f"SSRF block: IP {ip} matched blocked network {net}")
                raise SSRFSecurityError("Access to local or private network addresses is restricted.")
