"""Helpers for migrate templates integration."""

from enum import StrEnum
import itertools
import logging
from pathlib import Path
from typing import Any

from annotatedyaml.objects import NodeStrClass

from homeassistant.components.template.const import CONF_DEFAULT_ENTITY_ID
from homeassistant.const import ATTR_ENTITY_ID, CONF_NAME, CONF_PLATFORM, CONF_UNIQUE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import template
from homeassistant.helpers.script_variables import ScriptVariables
from homeassistant.helpers.typing import ConfigType

from .const import COMMON_LEGACY_FIELDS

_LOGGER = logging.getLogger(__name__)


def rewrite_legacy_to_modern_config(
    hass: HomeAssistant,
    entity_cfg: ConfigType,
    extra_legacy_fields: dict[str, str],
) -> ConfigType:
    """Rewrite legacy config."""
    entity_cfg = {**entity_cfg}

    # Remove deprecated entity_id field from legacy syntax
    entity_cfg.pop(ATTR_ENTITY_ID, None)

    # Remove platform if it exists.
    entity_cfg.pop(CONF_PLATFORM, None)

    for from_key, to_key in itertools.chain(
        COMMON_LEGACY_FIELDS.items(), extra_legacy_fields.items()
    ):
        if from_key not in entity_cfg or to_key in entity_cfg:
            continue

        val = entity_cfg.pop(from_key)
        if isinstance(val, str):
            val = template.Template(val, hass)
        entity_cfg[to_key] = val

    if CONF_NAME in entity_cfg and isinstance(entity_cfg[CONF_NAME], str):
        entity_cfg[CONF_NAME] = template.Template(entity_cfg[CONF_NAME], hass)

    return entity_cfg


def log_legacy_location(
    hass: HomeAssistant, domain: str, location: str, formatted_config: ConfigType
) -> None:
    """Log legacy location."""
    migration_path = Path(hass.config.path("migrated_templates")) / f"{domain}.yaml"
    location = (
        f"Found legacy template {domain} entity {location}, adding"
        if location
        else "Adding"
    )
    message = f"{location} {get_config_breadcrumbs(formatted_config)} migration configuration to {migration_path}"
    _LOGGER.info(message)


def rewrite_legacy_to_modern_configs(
    hass: HomeAssistant,
    domain: str,
    entity_cfg: dict[str, ConfigType],
    extra_legacy_fields: dict[str, str],
) -> list[ConfigType]:
    """Rewrite legacy configuration definitions to modern ones."""
    entities = []
    for object_id, entity_conf in entity_cfg.items():
        entity_conf = {**entity_conf, CONF_DEFAULT_ENTITY_ID: f"{domain}.{object_id}"}

        entity_conf = rewrite_legacy_to_modern_config(
            hass, entity_conf, extra_legacy_fields
        )

        if CONF_NAME not in entity_conf:
            entity_conf[CONF_NAME] = template.Template(object_id, hass)

        entities.append(entity_conf)
        log_legacy_location(
            hass, domain, _get_legacy_location_breadcrumb(object_id), entity_conf
        )

    return entities


def _format_template(value: Any, field: str | None = None) -> Any:
    if isinstance(value, template.Template):
        return value.template

    if isinstance(value, StrEnum):
        return value.value

    if isinstance(value, (int, float, str, bool)):
        return value

    return str(value)


def get_config_breadcrumbs(config: ConfigType) -> str:
    """Try to coerce entity information from the config."""
    breadcrumb = "Template Entity"
    # Default entity id should be in most legacy configuration because
    # it's created from the legacy slug. Vacuum and Lock do not have a
    # slug, therefore we need to use the name or unique_id.
    if (default_entity_id := config.get(CONF_DEFAULT_ENTITY_ID)) is not None:
        breadcrumb = default_entity_id.split(".")[-1]
    elif (unique_id := config.get(CONF_UNIQUE_ID)) is not None:
        breadcrumb = f"unique_id: {unique_id}"
    elif (name := config.get(CONF_NAME)) and isinstance(name, template.Template):
        breadcrumb = name.template
    return breadcrumb


def _get_legacy_location_breadcrumb(key: str | NodeStrClass) -> str:
    if isinstance(key, NodeStrClass):
        return f"at {key.__config_file__}, line {key.__line__}"

    return ""


def get_legacy_location_breadcrumb(config: ConfigType) -> str:
    """Try to get the legacy file location."""
    first_key = list(config.keys())[0]
    return _get_legacy_location_breadcrumb(first_key)


def format_migration_config(
    config: ConfigType | list[ConfigType], depth: int = 0
) -> ConfigType | list[ConfigType]:
    """Recursive method to format templates as strings from ConfigType."""
    if depth > 9:
        raise RecursionError

    if isinstance(config, list):
        items = []
        for item in config:
            if isinstance(item, (dict, list)):
                if len(item) > 0:
                    items.append(format_migration_config(item, depth + 1))
            else:
                items.append(_format_template(item))
        return items  # type: ignore[return-value]

    formatted_config = {}
    for field, value in config.items():
        if isinstance(field, NodeStrClass):
            field = str(field)

        if isinstance(value, dict):
            if len(value) > 0:
                formatted_config[field] = format_migration_config(value, depth + 1)
        elif isinstance(value, list):
            if len(value) > 0:
                formatted_config[field] = format_migration_config(value, depth + 1)
            else:
                formatted_config[field] = []
        elif isinstance(value, ScriptVariables):
            formatted_config[field] = format_migration_config(
                value.as_dict(), depth + 1
            )
        else:
            formatted_config[field] = _format_template(value)

    return formatted_config
