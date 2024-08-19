from __future__ import annotations

import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.template.const import CONF_AVAILABILITY_TEMPLATE
from homeassistant.components.template.template_entity import TemplateEntity
from homeassistant.components.water_heater import (
    ATTR_AWAY_MODE,
    ATTR_CURRENT_TEMPERATURE,
    ATTR_OPERATION_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    ENTITY_ID_FORMAT,
    STATE_ECO,
    STATE_ELECTRIC,
    STATE_GAS,
    STATE_HEAT_PUMP,
    STATE_HIGH_DEMAND,
    STATE_PERFORMANCE,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_ENTITY_PICTURE_TEMPLATE,
    CONF_ICON_TEMPLATE,
    CONF_NAME,
    CONF_UNIQUE_ID,
    STATE_OFF,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.script import Script
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

# Values
CONF_TEMP_MIN = "temperature_min"
CONF_TEMP_MAX = "temperature_max"
CONF_OPERATION_MODE_LIST = "operation_modes"

# Templates
CONF_CURRENT_TEMP_TEMPLATE = "current_temperature_template"
CONF_TARGET_TEMP_TEMPLATE = "target_temperature_template"
CONF_TARGET_TEMP_HIGH_TEMPLATE = "target_temperature_high_template"
CONF_TARGET_TEMP_LOW_TEMPLATE = "target_temperature_low_template"
CONF_IS_AWAY_MODE_ON_TEMPLATE = "is_away_mode_on_template"
CONF_CURRENT_OPERATION = "current_operation_template"
CONF_TEMP_MIN_TEMPLATE = "temperature_min_template"
CONF_TEMP_MAX_TEMPLATE = "temperature_max_template"

# Actions
CONF_SET_TEMP_ACTION = "set_temperature"
CONF_SET_AWAY_MODE_ACTION = "set_away_mode"
CONF_SET_OPERATION_ACTION = "set_operation"

# Helper
DEFAULT_NAME = "Template Water Heater"
DEFAULT_TEMP = 55
DOMAIN = "water_heater_template"

# Validation of the user's configuration
PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_AVAILABILITY_TEMPLATE): cv.template,
        vol.Optional(CONF_ICON_TEMPLATE): cv.template,
        vol.Optional(CONF_ENTITY_PICTURE_TEMPLATE): cv.template,
        vol.Optional(CONF_CURRENT_TEMP_TEMPLATE): cv.template,
        vol.Optional(CONF_TARGET_TEMP_TEMPLATE): cv.template,
        vol.Optional(CONF_TARGET_TEMP_HIGH_TEMPLATE): cv.template,
        vol.Optional(CONF_TARGET_TEMP_LOW_TEMPLATE): cv.template,
        vol.Optional(CONF_IS_AWAY_MODE_ON_TEMPLATE): cv.template,
        vol.Optional(CONF_CURRENT_OPERATION): cv.template,
        vol.Optional(CONF_TEMP_MIN_TEMPLATE): cv.template,
        vol.Optional(CONF_TEMP_MAX_TEMPLATE): cv.template,
        vol.Optional(CONF_SET_TEMP_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(CONF_SET_AWAY_MODE_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(CONF_SET_OPERATION_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(CONF_TEMP_MIN, default=DEFAULT_MIN_TEMP): vol.Coerce(float),
        vol.Optional(CONF_TEMP_MAX, default=DEFAULT_MAX_TEMP): vol.Coerce(float),
        vol.Optional(
            CONF_OPERATION_MODE_LIST,
            default=[
                STATE_ECO,
                STATE_ELECTRIC,
                STATE_PERFORMANCE,
                STATE_HIGH_DEMAND,
                STATE_HEAT_PUMP,
                STATE_GAS,
                STATE_OFF,
            ],
        ): cv.ensure_list,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: Callable,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the water heater template platform."""
    async_add_entities([WaterHeaterTemplate(hass, config)])


class WaterHeaterTemplate(TemplateEntity, WaterHeaterEntity, RestoreEntity):
    """Representation of a water heater template."""

    def __init__(self, hass: HomeAssistant, config: ConfigType) -> None:
        super().__init__(
            hass,
            availability_template=config.get(CONF_AVAILABILITY_TEMPLATE),
            icon_template=config.get(CONF_ICON_TEMPLATE),
            entity_picture_template=config.get(CONF_ENTITY_PICTURE_TEMPLATE),
        )
        self._hass = hass
        self._config = config
        entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, config[CONF_NAME], hass=hass
        )
        self._context = Context(user_id=entity_id)
        self._available = True  # TODO add available template

        self._attr_temperature_unit = hass.config.units.temperature_unit
        self._attr_name = config[CONF_NAME]
        self._attr_unique_id = config.get(CONF_UNIQUE_ID, None)
        self._attr_supported_features = 0
        self._attr_min_temp = config[CONF_TEMP_MIN]
        self._attr_max_temp = config[CONF_TEMP_MAX]
        self._attr_operation_list = config[CONF_OPERATION_MODE_LIST]

        self._current_temp = None
        self._target_temp = DEFAULT_TEMP
        self._target_temp_high = None
        self._target_temp_low = None
        self._is_away_mode_on = None
        self._current_operation = STATE_OFF

        self._current_temp_template = config.get(CONF_CURRENT_TEMP_TEMPLATE)
        self._target_temp_template = config.get(CONF_TARGET_TEMP_TEMPLATE)
        self._target_temp_high_template = config.get(CONF_TARGET_TEMP_HIGH_TEMPLATE)
        self._target_temp_low_template = config.get(CONF_TARGET_TEMP_LOW_TEMPLATE)
        self._is_away_mode_on_template = config.get(CONF_IS_AWAY_MODE_ON_TEMPLATE)
        self._current_operation_template = config.get(CONF_CURRENT_OPERATION)
        self._min_temp_template = config.get(CONF_TEMP_MIN_TEMPLATE)
        self._max_temp_template = config.get(CONF_TEMP_MAX_TEMPLATE)

        self._set_temp_script = None
        if set_temp_action := config.get(CONF_SET_TEMP_ACTION):
            self._set_temp_script = Script(
                hass, set_temp_action, self._attr_name, DOMAIN
            )
            self._attr_supported_features |= WaterHeaterEntityFeature.TARGET_TEMPERATURE

        self._set_away_mode_script = None
        if set_away_mode_action := config.get(CONF_SET_AWAY_MODE_ACTION):
            self._set_away_mode_script = Script(
                hass, set_away_mode_action, self._attr_name, DOMAIN
            )
            self._attr_supported_features |= WaterHeaterEntityFeature.AWAY_MODE

        self._set_operation_mode_script = None
        if set_operation_mode_action := config.get(CONF_SET_OPERATION_ACTION):
            self._set_operation_mode_script = Script(
                hass, set_operation_mode_action, self._attr_name, DOMAIN
            )
            self._attr_supported_features |= WaterHeaterEntityFeature.OPERATION_MODE

    @property
    def current_temperature(self) -> float | None:
        return self._current_temp

    @property
    def target_temperature(self) -> float | None:
        return self._target_temp

    @property
    def target_temperature_high(self) -> float | None:
        return self._target_temp_high

    @property
    def target_temperature_low(self) -> float | None:
        return self._target_temp_low

    @property
    def is_away_mode_on(self) -> bool | None:
        return self._is_away_mode_on

    @property
    def current_operation(self) -> str | None:
        return self._current_operation

    @property
    def operation_list(self) -> list[str] | None:
        return self._attr_operation_list

    def _update_current_temp(self, temp):
        if temp not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._current_temp = float(temp)
            except ValueError:
                _LOGGER.error("Could not parse temperature from %s", temp)

    def _update_target_temp(self, temp):
        if temp not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._target_temp = float(temp)
                self.hass.async_create_task(
                    self.async_set_temperature(**{ATTR_TEMPERATURE: self._target_temp})
                )
            except ValueError:
                _LOGGER.error("Could not parse temperature from %s", temp)

    def _update_target_temp_high(self, temp):
        if temp not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._target_temp_high = float(temp)
                self.hass.async_create_task(
                    self.async_set_temperature(
                        **{ATTR_TARGET_TEMP_HIGH: self._target_temp_high}
                    )
                )
            except ValueError:
                _LOGGER.error("Could not parse temperature high from %s", temp)

    def _update_target_temp_low(self, temp):
        if temp not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._target_temp_low = float(temp)
                self.hass.async_create_task(
                    self.async_set_temperature(
                        **{ATTR_TARGET_TEMP_LOW: self._target_temp_low}
                    )
                )
            except ValueError:
                _LOGGER.error("Could not parse temperature low from %s", temp)

    def _update_min_temp(self, temp):
        if temp not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._attr_min_temp = float(temp)
            except ValueError:
                _LOGGER.error("Could not parse min temperature from %s", temp)

    def _update_max_temp(self, temp):
        if temp not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._attr_max_temp = float(temp)
            except ValueError:
                _LOGGER.error("Could not parse max temperature from %s", temp)

    def _update_is_away_mode_on(self, state):
        if state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._is_away_mode_on = state
                if state:
                    self.hass.async_create_task(self.async_turn_away_mode_on())
                else:
                    self.hass.async_create_task(self.async_turn_away_mode_off())
            except ValueError:
                _LOGGER.error("Could not parse away_mode from %s", state)

    def _update_current_operation(self, operation):
        if operation in self._attr_operation_list:
            if self._current_operation != operation:
                self._current_operation = operation
                self.hass.async_create_task(self.async_set_operation_mode(operation))
        elif operation not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            _LOGGER.error(
                "Received invalid operation: %s. Expected: %s.",
                operation,
                self._attr_operation_list,
            )

    def _register_templates(self):
        if self._current_temp_template:
            self.add_template_attribute(
                "_current_temp",
                self._current_temp_template,
                None,
                self._update_current_temp,
                none_on_template_error=True,
            )

        if self._target_temp_template:
            self.add_template_attribute(
                "_target_temp",
                self._target_temp_template,
                None,
                self._update_target_temp,
                none_on_template_error=True,
            )

        if self._target_temp_high_template:
            self.add_template_attribute(
                "_target_temp_high",
                self._target_temp_high_template,
                None,
                self._update_target_temp_high,
                none_on_template_error=True,
            )

        if self._target_temp_low_template:
            self.add_template_attribute(
                "_target_temp_low",
                self._target_temp_low_template,
                None,
                self._update_target_temp_low,
                none_on_template_error=True,
            )

        if self._min_temp_template:
            self.add_template_attribute(
                "_attr_min_temp",
                self._min_temp_template,
                None,
                self._update_min_temp,
                none_on_template_error=True,
            )

        if self._max_temp_template:
            self.add_template_attribute(
                "_attr_max_temp",
                self._max_temp_template,
                None,
                self._update_max_temp,
                none_on_template_error=True,
            )

        if self._is_away_mode_on_template:
            self.add_template_attribute(
                "_is_away_mode_on",
                self._is_away_mode_on_template,
                None,
                self._update_is_away_mode_on,
                none_on_template_error=True,
            )

        if self._current_operation_template:
            self.add_template_attribute(
                "_curren_operation",
                self._current_operation_template,
                None,
                self._update_current_operation,
                none_on_template_error=True,
            )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None:
            if current_temp := state.attributes.get(ATTR_CURRENT_TEMPERATURE):
                self._current_temp = float(current_temp)

            if target_temp := state.attributes.get(ATTR_TEMPERATURE, DEFAULT_TEMP):
                self._target_temp = float(target_temp)

            if target_temp_high := state.attributes.get(ATTR_TARGET_TEMP_HIGH):
                self._target_temp_high = float(target_temp_high)

            if target_temp_low := state.attributes.get(ATTR_TARGET_TEMP_LOW):
                self._target_temp_low = float(target_temp_low)

            if is_away_mode_on := state.attributes.get(ATTR_AWAY_MODE):
                self._is_away_mode_on = bool(is_away_mode_on)

            if current_operation := state.attributes.get(
                ATTR_OPERATION_MODE, STATE_OFF
            ):
                self._current_operation = str(current_operation)

        self._register_templates()

    # TODO add state change to run variable
    async def async_set_temperature(self, **kwargs) -> None:
        if self._set_temp_script is not None:
            await self._set_temp_script.async_run(
                run_variables={
                    ATTR_TEMPERATURE: kwargs.get(ATTR_TEMPERATURE),
                    ATTR_TARGET_TEMP_HIGH: kwargs.get(ATTR_TARGET_TEMP_HIGH),
                    ATTR_TARGET_TEMP_LOW: kwargs.get(ATTR_TARGET_TEMP_LOW),
                },
                context=self._context,
            )
        else:
            self._target_temp = kwargs.get(ATTR_TEMPERATURE)
            self.async_write_ha_state()

    async def async_turn_away_mode_on(self):
        if self._set_away_mode_script is not None:
            await self._set_away_mode_script.async_run(
                run_variables={ATTR_AWAY_MODE: True},
                context=Context() if self._context is None else self._context,
            )
        else:
            self._is_away_mode_on = True
            self.async_write_ha_state()

    async def async_turn_away_mode_off(self):
        if self._set_away_mode_script is not None:
            await self._set_away_mode_script.async_run(
                run_variables={ATTR_AWAY_MODE: False}, context=self._context
            )
        else:
            self._is_away_mode_on = False
            self.async_write_ha_state()

    async def async_set_operation_mode(self, operation: str) -> None:
        if self._current_operation_template is None:
            self._curren_operation = operation
            self.async_write_ha_state()

        if self._set_operation_mode_script is not None:
            await self._set_operation_mode_script.async_run(
                run_variables={ATTR_OPERATION_MODE: operation}, context=self._context
            )
