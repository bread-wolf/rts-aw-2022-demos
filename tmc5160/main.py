import pytrinamic
from pytrinamic.connections import ConnectionManager
from pytrinamic.evalboards import TMC5160_eval
from helpers.Tmc5160_helpers import Tmc5160

pytrinamic.show_info()
with ConnectionManager().connect() as my_interface:
    demo = Tmc5160(my_interface, encoder_tick_per_turn=10000, steps_per_turn=200)
    demo.config_encoder()
    demo.config_ramper(vmax=2.0)
