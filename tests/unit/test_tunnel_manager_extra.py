import re
from unittest.mock import Mock

from bindu.tunneling.manager import TunnelManager


def test_invalid_port_type():
    manager = TunnelManager()

    try:
        manager.create_tunnel("not-int")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for non-integer port")


def test_invalid_port_range():
    manager = TunnelManager()

    try:
        manager.create_tunnel(70000)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for out-of-range port")


def test_generate_subdomain_from_did_normalizes_and_sanitizes():
    subdomain = TunnelManager._generate_subdomain_from_did("did:example:Agent_01@foo.bar!")

    assert subdomain == "example-agent-01-at-foo-bar"


def test_generate_subdomain_from_did_prefixes_when_not_starting_with_letter():
    subdomain = TunnelManager._generate_subdomain_from_did("123_service")

    assert subdomain == "a123-service"


def test_generate_subdomain_from_did_returns_agent_when_empty_after_sanitization():
    subdomain = TunnelManager._generate_subdomain_from_did("!!!")

    assert subdomain == "agent"


def test_generate_subdomain_from_did_truncates_to_dns_label_limit():
    long_did = "did:example:" + ("a" * 80)
    subdomain = TunnelManager._generate_subdomain_from_did(long_did)

    assert len(subdomain) == 63


def test_generate_subdomain_uses_letter_first_and_requested_length():
    subdomain = TunnelManager._generate_subdomain(length=16)

    assert len(subdomain) == 16
    assert subdomain[0].isalpha()
    assert re.fullmatch(r"[a-z0-9]+", subdomain)


def test_get_public_url_returns_none_when_no_active_tunnel():
    manager = TunnelManager()

    assert manager.get_public_url() is None


def test_get_public_url_returns_active_tunnel_url():
    manager = TunnelManager()
    manager.active_tunnel = Mock(public_url="https://unit.test")

    assert manager.get_public_url() == "https://unit.test"


def test_context_manager_exit_stops_tunnel_and_returns_false():
    manager = TunnelManager()
    manager.stop_tunnel = Mock()

    result = manager.__exit__(None, None, None)

    manager.stop_tunnel.assert_called_once()
    assert result is False
