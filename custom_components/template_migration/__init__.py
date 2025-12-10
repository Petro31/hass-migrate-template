"""Migrate legacy template helper."""

from functools import partial
import logging
from pathlib import Path

import yaml

from homeassistant.components.template import DOMAIN as TEMPLATE_DOMAIN
from homeassistant.components.template.helpers import DATA_DEPRECATION
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.service import ServiceCall, async_register_admin_service
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


SERVICE_GENERATE_MIGRATION_YAML = "generate_yaml"


class TemplateDumper(yaml.Dumper):
    """Custom YAML dumper for template migration."""

    def represent_scalar(
        self, tag: str, value, style: str | None = None
    ) -> yaml.ScalarNode:
        """Represent scalar values with custom style for templates."""
        if "{{" in value or "{%" in value:
            style = ">"
        return super().represent_scalar(tag, value, style)


def create_migrated_file(path: Path, configs: list[ConfigType]) -> None:
    """Create a migrated YAML file."""
    with path.open("w", encoding="utf-8") as yaml_file:
        yaml.dump(
            configs,
            yaml_file,
            Dumper=TemplateDumper,
            allow_unicode=True,
            sort_keys=False,
        )
    _LOGGER.info("Created migrated template YAML file at %s", path)


async def generate_migration_yaml(hass: HomeAssistant) -> None:
    """Generate migration YAML for legacy template helper."""
    if (found_issues := hass.data.pop(DATA_DEPRECATION, None)) is not None:
        migrated: dict[str, list[ConfigType]] = {}

        issue_registry = ir.async_get(hass)

        for issue_id in found_issues:
            if (
                issue := issue_registry.async_get_issue(TEMPLATE_DOMAIN, issue_id)
            ) is not None and issue.translation_placeholders is not None:
                if (domain := issue.translation_placeholders.get("domain")) and (
                    issue_yaml := issue.translation_placeholders.get("config")
                ):
                    if domain not in migrated:
                        migrated[domain] = []

                    issue_yaml = issue_yaml.replace("```", "").strip()
                    config: ConfigType = yaml.safe_load(issue_yaml)

                    if sub_configs := config.pop(TEMPLATE_DOMAIN, None):
                        for sub_config in sub_configs:
                            migrated[domain].append(sub_config)

        if migrated:
            migration_path = Path(hass.config.path("migrated_templates"))
            if not migration_path.exists():
                migration_path.mkdir()
                _LOGGER.info(
                    "Created template migration directory at %s", migration_path
                )

            for domain, configs in migrated.items():
                yaml_path = migration_path / f"{domain}.yaml"
                if yaml_path.exists():
                    _LOGGER.warning(
                        "Overwriting existing migration file at %s", yaml_path
                    )

                await hass.async_add_executor_job(
                    partial(create_migrated_file, yaml_path, configs)
                )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the legacy template migration helper integration."""

    async def _service_handler(_: ServiceCall) -> None:
        """Generate migration YAML service handler."""
        await generate_migration_yaml(hass)

    async_register_admin_service(
        hass, DOMAIN, SERVICE_GENERATE_MIGRATION_YAML, _service_handler
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up template migration from a config entry."""

    await hass.config_entries.async_forward_entry_setups(entry, [])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, [])
