"""Migrate legacy template helper."""

from functools import partial
import logging
from pathlib import Path

import yaml

from homeassistant.components.template import DOMAIN as TEMPLATE_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PLATFORM
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service import ServiceCall, async_register_admin_service
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, LEGACY_FIELDS, LEGACY_KEYS
from .helpers import (
    format_migration_config,
    get_legacy_location_breadcrumb,
    log_legacy_location,
    rewrite_legacy_to_modern_config,
    rewrite_legacy_to_modern_configs,
)

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


async def generate_migration_yaml(hass: HomeAssistant, config: ConfigType) -> None:
    """Generate migration YAML for legacy template helper."""

    migrated: dict[str, list[str]] = {}
    for domain, extra_legacy_fields in LEGACY_FIELDS.items():
        if (platform_configs := config.get(domain)) is not None:
            if isinstance(platform_configs, list):
                for platform_config in platform_configs:
                    if (
                        isinstance(platform_config, dict)
                        and platform_config.get(CONF_PLATFORM) == TEMPLATE_DOMAIN
                    ):
                        location = get_legacy_location_breadcrumb(platform_config)
                        if domain not in migrated:
                            migrated[domain] = []

                        if (legacy_key := LEGACY_KEYS.get(domain)) is None:
                            migrated_config = rewrite_legacy_to_modern_config(
                                hass, platform_config, extra_legacy_fields
                            )
                            formatted_config = format_migration_config(migrated_config)
                            log_legacy_location(
                                hass, domain, location, formatted_config
                            )
                            migrated[domain].append({domain: [formatted_config]})

                        if legacy_configs := platform_config.get(legacy_key):
                            if location:
                                cnt = len(legacy_configs)
                                message = f"Found {cnt} legacy template {domain} entit{'ies' if cnt > 1 else 'y'} {location}"
                                _LOGGER.info(message)
                            for migrated_config in rewrite_legacy_to_modern_configs(
                                hass, domain, legacy_configs, extra_legacy_fields
                            ):
                                formatted_config = format_migration_config(
                                    migrated_config
                                )
                                migrated[domain].append({domain: [formatted_config]})

    if not migrated:
        return

    migration_path = Path(hass.config.path("migrated_templates"))
    if not migration_path.exists():
        migration_path.mkdir()
        _LOGGER.info("Created template migration directory at %s", migration_path)

    for domain, configs in migrated.items():
        yaml_path = migration_path / f"{domain}.yaml"
        if yaml_path.exists():
            _LOGGER.warning("Overwriting existing migration file at %s", yaml_path)

        await hass.async_add_executor_job(
            partial(create_migrated_file, yaml_path, configs)
        )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the legacy template migration helper integration."""

    async def _service_handler(_: ServiceCall) -> None:
        """Generate migration YAML service handler."""
        await generate_migration_yaml(hass, config)

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
