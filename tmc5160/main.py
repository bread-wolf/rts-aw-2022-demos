import pytrinamic
from helpers.config import Tmc5160Config
from pytrinamic.connections import ConnectionManager
from pytrinamic.evalboards import TMC5160_eval

pytrinamic.show_info()
with ConnectionManager().connect() as my_interface:
    configurator = Tmc5160Config(my_interface, encoder_tick_per_turn=10000, steps_per_turn=200)
    configurator.config_encoder()
    configurator.config_ramper(vmax=1.0)
