"""sigall_mode_for_version: which SIG_ALL message format a mint version speaks.

Nutshell flipped to the spec message format at 0.20.3 (verified live
2026-09-27: 0.20.3+ rejects the legacy message with '0 < 1' and accepts
spec-format signatures; <=0.20.2 the reverse). Everything else — cdk,
cashu-cf, unknown — uses the standard spec format.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance.builder import sigall_mode_for_version


def test_nutshell_before_0203_is_legacy():
    assert sigall_mode_for_version("Nutshell/0.16.5") == "legacy"
    assert sigall_mode_for_version("Nutshell/0.20.2") == "legacy"


def test_nutshell_0203_and_later_is_standard():
    assert sigall_mode_for_version("Nutshell/0.20.3") == "standard"
    assert sigall_mode_for_version("Nutshell/0.21.0") == "standard"
    assert sigall_mode_for_version("Nutshell/9.9.9") == "standard"


def test_non_nutshell_is_standard():
    assert sigall_mode_for_version("cdk-mintd/0.17.6") == "standard"
    assert sigall_mode_for_version("cashu-cf 1.2.3") == "standard"
    assert sigall_mode_for_version("some-mint") == "standard"


def test_nutshell_with_cf_tag_is_standard():
    assert sigall_mode_for_version("cashu-cf nutshell 0.19.0") == "standard"


def test_unparseable_nutshell_version_stays_legacy():
    assert sigall_mode_for_version("Nutshell/develop-abc123") == "legacy"
    assert sigall_mode_for_version("Nutshell/") == "legacy"
