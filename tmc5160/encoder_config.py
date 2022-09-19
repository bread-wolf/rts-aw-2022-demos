"""
TMC5160 can function with stepper motors equipped with ABN encoders.

The encoder needs to be configured in the registers ENC_MODE and ENC_CONST.
The encoder constant represents the number of microsteps per encoder tick:

Constant = (microstep_per_fullstep * fullsteps_per_turn) / Encoder_resolution
The constant needs to be then converted to be written into TMC5160, e.g. for 12.5

If Decimal mode is used in ENC_MODE.ENC_SEL_DECIMAL
- An integer part of 12 written to ENC_CONST.INTEGER
- A decimal part of 5 written to ENC_CONST.DECIMAL

If Decimal is turned off in ENC_MODE, 12.5 needs to be converted to a Q16.16 fixed point number:
- Integer will be 12 as well
- Decimal part will be 5 // (1 / 2^16)
"""
import pytrinamic
from pytrinamic.connections import ConnectionManager
from pytrinamic.evalboards import TMC5160_eval

# System parameters
microsteps_per_fullstep = 256  # This is the default value in TMC5160, can be configured in CHOPCONF.MRES
fullsteps_per_turn = 200  # This is usually 200, or 400 on precision steppers.
encoder_resolution = 10000  # This should be written on the encoder body, usually called P/R on trinamic encoders.

# Calculating constants for the Q16.16 number mode (default mode)
encoder_constant = (200 * 256) / 10000
encoder_constant_integer = int(encoder_constant)
encoder_constant_fraction = int((encoder_constant - encoder_constant_integer) / (1 / (1 << 16)))


pytrinamic.show_info()
with ConnectionManager().connect() as my_interface:
    print(my_interface)

    tmc_eval = TMC5160_eval(my_interface)  # Create TMC5160-EVAL class which communicates over the Landungsbrücke via TMCL
    tmc_ic = tmc_eval.ics[0]  # tmc_ic is for writing registers and using low level functions
    tmc_motor = tmc_eval.motors[0]  # tmc_motor is gor using axis parameters, i.e. high level functions like ramping

    # Writing the encoder config registers
    tmc_eval.write_register_field(tmc_ic.FIELD.ENC_SEL_DECIMAL, False)  # Use the Q16.16 mode
    tmc_eval.write_register_field(tmc_ic.FIELD.INTEGER, encoder_constant_integer)
    tmc_eval.write_register_field(tmc_ic.FIELD.FRACTIONAL, encoder_constant_fraction)
    print("Writing ABN Encoder settings:")
    print(f"Microsteps: {microsteps_per_fullstep}, Motor Steps: {fullsteps_per_turn}, Encoder resolution: {encoder_resolution}")
    print(f"Q16.16: {encoder_constant} -> Int: 0x{encoder_constant_integer:04X}, Frac: 0x{encoder_constant_fraction:04X}")
