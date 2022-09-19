import time

import pytrinamic
from pytrinamic.connections import ConnectionManager
from pytrinamic.evalboards import TMC5160_eval

pytrinamic.show_info()

with ConnectionManager().connect() as my_interface:
    print(my_interface)

    tmc_eval = TMC5160_eval(my_interface)  # Create TMC5160-EVAL class which communicates over the Landungsbrücke via TMCL
    tmc_ic = tmc_eval.ics[0]  # tmc_ic is for writing registers and using low level functions
    tmc_motor = tmc_eval.motors[0]  # tmc_motor is gor using axis parameters, i.e. high level functions like ramping

    print("Preparing parameters...")
    tmc_eval.write_register(tmc_ic.REG.A1, 1000)
    tmc_eval.write_register(tmc_ic.REG.V1, 50000)
    tmc_eval.write_register(tmc_ic.REG.D1, 500)
    tmc_eval.write_register(tmc_ic.REG.DMAX, 500)
    tmc_eval.write_register(tmc_ic.REG.VSTART, 0)
    tmc_eval.write_register(tmc_ic.REG.VSTOP, 10)
    tmc_eval.write_register(tmc_ic.REG.AMAX, 1000)

    # Set lower run/standby current
    motorCurrent = 2
    tmc_motor.set_axis_parameter(tmc_motor.AP.MaxCurrent, motorCurrent)
    tmc_motor.set_axis_parameter(tmc_motor.AP.StandbyCurrent, motorCurrent)

    # Clear actual positions
    tmc_motor.actual_position = 0

    print("Rotating...")
    tmc_motor.rotate(7 * 25600)
    time.sleep(5)

    print("Stopping...")
    tmc_motor.stop()
    time.sleep(1)

    print("Moving back to 0...")
    tmc_motor.move_to(0, 7 * 25600)

    # Wait until position 0 is reached
    while tmc_motor.actual_position != 0:
        print("Actual position: " + str(tmc_motor.actual_position))
        time.sleep(0.2)

    print("Reached position 0")

print("\nReady.")
