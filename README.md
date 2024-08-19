# Water Heater Template
[![HACS Badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![License](https://img.shields.io/github/license/sthomsen1/ha-water-heater-template?=style=for-the-badge)](https://github.com/sthomsen1/ha-water-heater-template/blob/main/LICENSE)
[![Code style](https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge)](https://github.com/psf/black)

Welcome to the 'water_heater_template' integration for Home Assistant! This integration allows you to create a fully customizable water heater entity using templates and actions, giving you the flexibility to define its behavior and properties based on your specific needs.

## Configuration


| Name                             | Type                                                                      | Description | Default Value |
| -------------------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| name                             | `string` | The name of the climate device. | "Template Water Heater" |
| unique_id                             | `string` | The [unique id](https://developers.home-assistant.io/docs/entity_registry_index/#unique-id) of the climate entity.| None |
| icon_template                    | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Defines a template for the icon of the device. ||
| entity_picture_template          | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Defines a template for the entity picture of the device. ||
| availability_template            | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Defines a template to get the `available` state of the component. If the template returns `true`, the device is `available`. If the template returns any other value, the device will be `unavailable`. If `availability_template` is not configured, the component will always be `available`. | true |
| current_temperature_template            | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Defines a template to get the current temperature. ||
| target_temperature_template            | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Defines a template to get the target temperature low temperature. ||
| target_temperature_high_template            | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Defines a template to get the target high temperature. || 
| target_temperature_low_template            | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Defines a template to get the target temperature low temperature. ||
| is_away_mode_on_template            | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Defines a template to check if the away mode is on. ||
| current_operation_template            | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Defines a template to get the current operation mode. ||
| temperature_min_template            | [`template`](https://www.home-assistant.io/docs/configuration/templating) |  Defines a template to get the minimum temperature. ||                     
| temperature_max_template            | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Defines a template to get the maximum temperature. ||                      
||| 
| set_temperature            |[`action`](https://www.home-assistant.io/docs/scripts)  | Action to be executed when the temperature is set. `temperature`, `target_temp_high`, `target_temp_low` variable can be used ||
| set_away_mode            | [`action`](https://www.home-assistant.io/docs/scripts)  | Action to be executed when the away mode is toggled. `away_mode` variable can be used  ||               
| set_operation            | [`action`](https://www.home-assistant.io/docs/scripts)  | Action to be executed when the operation mode is changed. `operation` variable can be used ||
|||                                                                              
| temperature_min            | `float` | Minimum temperature that can be defined ||
| temperature_max            | `float` | Maximum temperature that can be defined ||
| operation_modes            | `list` | A list of supported operation modes. Only default values are allowed | ['eco', 'electric', 'performance', 'high_demand', 'heat_pump', 'gas', 'off'] |
|||                                                                              


## Example Configuration

```yaml
- platform: water_heater_template
  name: "Warmwater"
  availability_template: "{{ is_state('sensor.warm_water_storage', 'on') }}"
  current_temperature_template: "{{ states('sensor.warm_water_storage_temp') }}"
  target_temperature_template: "{{ states('sensor.warm_water_storage_temp_desired') }}"
  temperature_min: 50
  temperature_max: 70
  target_temperature_high_template: "{{ float(states('sensor.warm_water_storage_temp_desired')) + float(states('sensor.warm_water_storage_temp_desired_offset')) }}"
  target_temperature_low_template: "{{ float(states('sensor.warm_water_storage_temp_desired')) - float(states('sensor.warm_water_storage_temp_hyst')) }}"
  current_operation_template: >
    {% if is_state('sensor.warm_water_state', 'off') %}
      off
    {% elif is_state('sensor.warm_water_state', 'load') %}
      performance
    {% elif is_state('sensor.warm_water_state', 'auto') %}
      eco
    {% else %}
      unknown
    {% endif %}
  operation_modes: ["eco", "off", "performance"]
  set_operation:
    choose:
      - conditions:
          - condition: template
            value_template: "{{ operation == 'performance' }}"
        sequence:
          - service: script.turn_on
            target:
              entity_id: script.heat_warm_water
      - conditions:
          - condition: template
            value_template: "{{ operation == 'eco' }}"
        sequence:
          - service: script.turn_on
            target:
              entity_id: script.warm_water_normal
      - conditions:
          - condition: template
            value_template: "{{ operation == 'off' }}"
        sequence:
          - service: script.turn_on
            target:
              entity_id: script.turn_off_warm_water
    default: []
  set_temperature:
    - condition: template
      value_template: "{{ is_number(temperature) }}"
    - service: script.set_warm_water_via_mqtt
      data:
        temperature: "{{ temperature | float }}"
```
