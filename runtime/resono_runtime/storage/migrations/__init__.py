from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import sqlite3

from .v005_runtime_foundation import apply as apply_v005
from .v006_agent_audiences import apply as apply_v006
from .v007_skill_catalog import apply as apply_v007
from .v008_plugin_catalog import apply as apply_v008
from .v009_plugin_components import apply as apply_v009
from .v010_mcp_connections import apply as apply_v010
from .v011_mcp_tools import apply as apply_v011
from .v012_mcp_configuration import apply as apply_v012
from .v013_connection_credentials import apply as apply_v013
from .v014_connections import apply as apply_v014
from .v015_mail import apply as apply_v015
from .v016_mail_confirmation import apply as apply_v016
from .v017_mcp_lifecycle import apply as apply_v017
from .v018_import_recovery import apply as apply_v018
from .v019_mail_sync_progress import apply as apply_v019
from .v020_mail_sent_parity import apply as apply_v020
from .v021_creations import apply as apply_v021
from .v022_plugin_component_ownership import apply as apply_v022
from .v023_import_recovery_phase import apply as apply_v023
from .v024_mail_utterance_approval import apply as apply_v024
from .v025_creation_sources import apply as apply_v025
from .v026_direct_handoffs import apply as apply_v026
from .v027_plugin_cards import apply as apply_v027
from .v028_calendar import apply as apply_v028
from .v029_tasks import apply as apply_v029
from .v030_calendar_connection_kind import apply as apply_v030
from .v031_remove_handoff_inspection import apply as apply_v031
from .v032_background_agent_runs import apply as apply_v032
from .v033_background_agent_settings import apply as apply_v033
from .v034_background_agent_recipes import apply as apply_v034
from .v035_background_agent_global_tools import apply as apply_v035
from .v036_workspace import apply as apply_v036
from .v037_workspace_tools import apply as apply_v037
from .v038_goal_context import apply as apply_v038
from .v039_agent_deliveries import apply as apply_v039
from .v040_goal_provenance_and_delivery_lease import apply as apply_v040
from .v041_goal_verification_contract import apply as apply_v041


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    apply: Callable[[sqlite3.Connection], None]


MIGRATIONS = (
    Migration(5, apply_v005),
    Migration(6, apply_v006),
    Migration(7, apply_v007),
    Migration(8, apply_v008),
    Migration(9, apply_v009),
    Migration(10, apply_v010),
    Migration(11, apply_v011),
    Migration(12, apply_v012),
    Migration(13, apply_v013),
    Migration(14, apply_v014),
    Migration(15, apply_v015),
    Migration(16, apply_v016),
    Migration(17, apply_v017),
    Migration(18, apply_v018),
    Migration(19, apply_v019),
    Migration(20, apply_v020),
    Migration(21, apply_v021),
    Migration(22, apply_v022),
    Migration(23, apply_v023),
    Migration(24, apply_v024),
    Migration(25, apply_v025),
    Migration(26, apply_v026),
    Migration(27, apply_v027),
    Migration(28, apply_v028),
    Migration(29, apply_v029),
    Migration(30, apply_v030),
    Migration(31, apply_v031),
    Migration(32, apply_v032),
    Migration(33, apply_v033),
    Migration(34, apply_v034),
    Migration(35, apply_v035),
    Migration(36, apply_v036),
    Migration(37, apply_v037),
    Migration(38, apply_v038),
    Migration(39, apply_v039),
    Migration(40, apply_v040),
    Migration(41, apply_v041),
)
LATEST_VERSION = MIGRATIONS[-1].version
