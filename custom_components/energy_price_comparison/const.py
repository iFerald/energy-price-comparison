DOMAIN = "energy_price_comparison"

CONF_PRICE_ENTITY = "price_entity"
CONF_ENERGY_ENTITY = "energy_entity"

DEFAULT_PRICE_ENTITY = "sensor.rce_pse_price"
DEFAULT_ENERGY_ENTITY = "sensor.deye_daily_energy_bought"

# G11 config keys
CONF_G11_RATE = "g11_rate_pln_per_kwh"
DEFAULT_G11_RATE = 0.4982


# G12 config keys
CONF_G12_DAY_RATE = "g12_day_rate_pln_per_kwh"
CONF_G12_NIGHT_RATE = "g12_night_rate_pln_per_kwh"

CONF_G12_DAY_RANGE_1_START = "g12_day_range_1_start"
CONF_G12_DAY_RANGE_2_SUMMER_START = "g12_day_range_2_summer_start"
CONF_G12_DAY_RANGE_2_WINTER_START = "g12_day_range_2_winter_start"

CONF_G12_NIGHT_RANGE_1_SUMMER_START = "g12_night_range_1_summer_start"
CONF_G12_NIGHT_RANGE_1_WINTER_START = "g12_night_range_1_winter_start"
CONF_G12_NIGHT_RANGE_2_START = "g12_night_range_2_start"

# G12 defaults
DEFAULT_G12_DAY_RATE = 0.5656
DEFAULT_G12_NIGHT_RATE = 0.3718

DEFAULT_G12_DAY_RANGE_1_START = "06:00"
DEFAULT_G12_DAY_RANGE_2_SUMMER_START = "17:00"
DEFAULT_G12_DAY_RANGE_2_WINTER_START = "15:00"

DEFAULT_G12_NIGHT_RANGE_1_SUMMER_START = "15:00"
DEFAULT_G12_NIGHT_RANGE_1_WINTER_START = "13:00"
DEFAULT_G12_NIGHT_RANGE_2_START = "22:00"
