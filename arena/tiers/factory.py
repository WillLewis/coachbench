from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .bridge import TieredAgent
from .declarative import Tier0Adapter, load_tier0_config
from .prompt_policy import Tier1Adapter, load_tier1_config
from .remote_endpoint import Tier2Adapter, Tier2Config


def tiered_agent_from_submission(row: dict[str, Any], secrets_root: Path | None = None, http_client: Any = None) -> TieredAgent:
    tier = row["access_tier"]
    side = row["side"]
    if tier == "declarative":
        adapter = Tier0Adapter(load_tier0_config(Path(row["tier_config_path"])))
    elif tier == "prompt_policy":
        adapter = Tier1Adapter(load_tier1_config(Path(row["tier_config_path"])))
    elif tier == "remote_endpoint":
        config_payload = json.loads(Path(row["tier_config_path"]).read_text(encoding="utf-8"))
        config = Tier2Config(**config_payload)
        secret_path = (secrets_root or Path("arena/storage/local/secrets/endpoints")) / f"{row['agent_id']}.json"
        secret = json.loads(secret_path.read_text(encoding="utf-8"))
        adapter = Tier2Adapter(config, secret["endpoint_url"], secret.get("api_key"), http_client=http_client, agent_id=row["agent_id"])
    else:
        raise ValueError(f"unsupported public tier factory: {tier}")
    return TieredAgent(adapter, side=side, name=row["label"])
