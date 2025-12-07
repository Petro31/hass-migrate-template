# Legacy Template Migration Helper

[![hacs_badge](https://img.shields.io/badge/HACS-Ready-blue.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
<br><a href="https://www.buymeacoffee.com/Petro31" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-black.png" width="150px" height="35px" alt="Buy Me A Coffee" style="height: 35px !important;width: 150px !important;" ></a>

This integration helps automatically migrate legacy template sensor issues into modern template entities.  Requires Home Assistant 2025.12 or later.

<h1><a class="title-link" name="installation" href="#installation"></a>Installation</h1>

## With HACS

1.  Install the integration through HACS using the button below or by adding `https://github.com/Petro31/hass-migrate-template` to HACS.

    [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Petro31&repository=hass-migrate-template&category=integration)
2. Restart Home Assistant
3. Add Legacy Template Migration Helper in integrations

## Without HACS

1. Copy the contents of `custom_components/template_migration/` to `<config>/custom_components/template_migration/`
2. Restart Home Assistant
3. Add Legacy Template Migration Helper in integrations

<h1><a class="title-link" name="use" href="#use"></a>Directions</h1>

1.  In **Developer Tools** -> **Actions** tab, select the `template_migration.generate_yaml` action.
    
    [![Open your Home Assistant instance and show your action developer tools.](https://my.home-assistant.io/badges/developer_services.svg)](https://my.home-assistant.io/redirect/developer_services/)
3.  Click **Perform action**
4.  A folder will be generated inside your configuration.  This folder will be named `migrated_templates` and it will contain mutliple files.  Each file will be a `domain` and it will contain all templates in that domain.
5.  Add `template migrated: !include_dir_merge_list migrated_templates` inside `configuration.yaml`.

    Note: Add this exactly as written above, even if you have a top-level `template:` defined already in your configuration. It uses the label `migrated`, and so will be merged with any other existing templates you may have defined.
7.  Verify the yaml loads properly by checking the configuration in **Developer Tools** -> **YAML** tab, **Check configuration** button.
    
    [![Open your Home Assistant instance and show your server controls.](https://my.home-assistant.io/badges/server_controls.svg)](https://my.home-assistant.io/redirect/server_controls/)
8.  Remove all references to the legacy templates provided by each repair.
9.  Be careful, make sure **Check configuration** passes before restarting Home Assistant. Restart Home Assistant.
