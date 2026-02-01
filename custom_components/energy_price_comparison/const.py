DOMAIN = "energy_price_comparison"

CONF_PRICE_ENTITY = "price_entity"
CONF_ENERGY_ENTITY = "energy_entity"  # deprecated
CONF_TOTAL_ENERGY_ENTITY = "total_energy_entity"

DEFAULT_PRICE_ENTITY = "sensor.rce_pse_price"
DEFAULT_ENERGY_ENTITY = "sensor.deye_daily_energy_bought"  # deprecated
DEFAULT_TOTAL_ENERGY_ENTITY = "sensor.deye_total_energy_bought"

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

# --- NEW: G12w config keys + defaults ---
CONF_G12W_DAY_RATE = "g12w_day_rate_pln_per_kwh"
CONF_G12W_NIGHT_RATE = "g12w_night_rate_pln_per_kwh"
DEFAULT_G12W_DAY_RATE = 0.5821
DEFAULT_G12W_NIGHT_RATE = 0.4235

# --- NEW: G12n config keys + defaults ---
CONF_G12N_DAY_RATE = "g12n_day_rate_pln_per_kwh"
CONF_G12N_NIGHT_RATE = "g12n_night_rate_pln_per_kwh"
DEFAULT_G12N_DAY_RATE = 0.5511
DEFAULT_G12N_NIGHT_RATE = 0.3912

# --- NEW: G12w ranges (HH:MM) ---
CONF_G12W_DAY_RANGE_1_START = "g12w_day_range_1_start"
CONF_G12W_DAY_RANGE_2_SUMMER_START = "g12w_day_range_2_summer_start"
CONF_G12W_DAY_RANGE_2_WINTER_START = "g12w_day_range_2_winter_start"
CONF_G12W_NIGHT_RANGE_1_SUMMER_START = "g12w_night_range_1_summer_start"
CONF_G12W_NIGHT_RANGE_1_WINTER_START = "g12w_night_range_1_winter_start"
CONF_G12W_NIGHT_RANGE_2_START = "g12w_night_range_2_start"

DEFAULT_G12W_DAY_RANGE_1_START = "06:00"
DEFAULT_G12W_DAY_RANGE_2_SUMMER_START = "17:00"
DEFAULT_G12W_DAY_RANGE_2_WINTER_START = "15:00"
DEFAULT_G12W_NIGHT_RANGE_1_SUMMER_START = "15:00"
DEFAULT_G12W_NIGHT_RANGE_1_WINTER_START = "13:00"
DEFAULT_G12W_NIGHT_RANGE_2_START = "22:00"

# --- NEW: G12n ranges (HH:MM) ---
CONF_G12N_DAY_START = "g12n_day_start"
CONF_G12N_NIGHT_START = "g12n_night_start"
DEFAULT_G12N_DAY_START = "05:00"
DEFAULT_G12N_NIGHT_START = "01:00"
