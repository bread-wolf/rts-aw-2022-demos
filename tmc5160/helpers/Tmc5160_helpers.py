import pytrinamic
from pytrinamic.connections import ConnectionManager
from pytrinamic.evalboards import TMC5160_eval


class Tmc5160:
    """
    This class automates configuration tasks to build more complex examples using TMC5160.

    Class attributes:
    - interface: Interface from connection manager.
    - clk_freq: TMC5160 clock frequency in hertz
    - encoder_tick_per_turn: Number of steps per turn the ABN encoder provides, usually P/R on Trinamic encoders
    - microsteps: Microstep setting for motor, number of microsteps per step, default is 256
    - steps_per_turn: Number of steps of stepper motor, usually 200.
    """

    def __init__(self, interface, steps_per_turn=200, clk_freq=12000000, encoder_tick_per_turn=None) -> None:
        # Initialize class attributes
        self.interface = interface
        self.ckl_freq = clk_freq
        self.encoder_tick_per_turn = encoder_tick_per_turn
        self.steps_per_turn = steps_per_turn

        # Create eval connection attributes
        self.tmc_eval = TMC5160_eval(interface)
        self.tmc_ic = self.tmc_eval.ics[0]
        self.tmc_motor = self.tmc_eval.motors[0]

        # Read microstep value from registers
        mres = self.tmc_eval.read_register_field(self.tmc_ic.FIELD.MRES)
        self.microsteps = None
        if mres == 0:
            self.microsteps = 256
        elif mres == 8:
            self.microsteps = 1
        else:
            self.microsteps = 256 / (1 << mres)

    def config_encoder(self, encoder_tick_per_turn=None):
        """
        Configures ABN encoder interface for TMC5160.
        """
        if self.encoder_tick_per_turn is None:
            if encoder_tick_per_turn is None:
                raise ValueError(
                    "Must provide an encoder tick per turn value!! None was provided either at init, or when calling this function!"
                )

        # If user already provided a value at init, and now provides a new one, replace old one with new one.
        if self.encoder_tick_per_turn is not None and encoder_tick_per_turn is not None:
            self.encoder_tick_per_turn = encoder_tick_per_turn

        # Calculating constants for the Q16.16 number mode (default mode)
        encoder_constant = (self.steps_per_turn * self.microsteps) / self.encoder_tick_per_turn
        encoder_constant_integer = int(encoder_constant)
        encoder_constant_fraction = int((encoder_constant - encoder_constant_integer) / (1 / (1 << 16)))

        # Writing the encoder config registers
        self.tmc_eval.write_register_field(self.tmc_ic.FIELD.ENC_SEL_DECIMAL, False)  # Use the Q16.16 mode
        self.tmc_eval.write_register_field(self.tmc_ic.FIELD.INTEGER, encoder_constant_integer)
        self.tmc_eval.write_register_field(self.tmc_ic.FIELD.FRACTIONAL, encoder_constant_fraction)
        print("Writing ABN Encoder settings:")
        print(
            f"Microsteps: {self.microsteps}, Motor Steps: {self.steps_per_turn}, Encoder resolution: {self.encoder_tick_per_turn}"
        )
        print(f"Q16.16: {encoder_constant} -> Int: 0x{encoder_constant_integer:04X}, Frac: 0x{encoder_constant_fraction:04X}")

    def config_ramper(self, vstart=0.05, a1=100.0, v1=0.7, amax=70.0, vmax=1.5, dmax=60.0, d1=90.0, vstop=0.05):
        """
        See README for details on ramper, or datasheet.
        All velocities are in rps, all accelerations in rps^2 (rotations per seconds, rotations per second per second)

        rps can be converted to and from radians using the factor 2*pi.

        Clock frequency needs to be known to convert real life velocity and acceleration to microsteps-based units.
        - Velocity is in µsteps/s = v_internal * (clk_freq / 2 / 2^23)
        - Acceleration is in µsteps/s^2 = a_internal * clk_freq^2 / (512 * 256) / 2^24
        - Ramp steps are in µsteps = v_internal^2 / a_internal / 2^8

        To convert from µps to rps, simply divide by the number of microsteps per turn or (microsteps * steps_per_turn)
        """
        # Convert all units to internal
        vstart_int = self.rps_velocity_to_internal_velocity(vstart)
        a1_int = self.rps_acceleration_to_internal_acceleration(a1)
        v1_int = self.rps_velocity_to_internal_velocity(v1)
        amax_int = self.rps_acceleration_to_internal_acceleration(amax)
        vmax_int = self.rps_velocity_to_internal_velocity(vmax)
        dmax_int = self.rps_acceleration_to_internal_acceleration(dmax)
        d1_int = self.rps_acceleration_to_internal_acceleration(d1)
        vstop_int = self.rps_velocity_to_internal_velocity(vstop)

        # Write registers
        self.tmc_eval.write_register(self.tmc_ic.REG.A1, a1_int)
        self.tmc_eval.write_register(self.tmc_ic.REG.V1, v1_int)
        self.tmc_eval.write_register(self.tmc_ic.REG.D1, d1_int)
        self.tmc_eval.write_register(self.tmc_ic.REG.DMAX, dmax_int)
        self.tmc_eval.write_register(self.tmc_ic.REG.VSTART, vstart_int)
        self.tmc_eval.write_register(self.tmc_ic.REG.VSTOP, vstop_int)
        self.tmc_eval.write_register(self.tmc_ic.REG.AMAX, amax_int)
        self.tmc_eval.write_register(self.tmc_ic.REG.VMAX, vmax_int)

        # Pretty print some stuff
        print(f"Written VSTART to {vstart_int} internal units (requested {vstart} rps)")
        print(f"Written A1 to {a1_int} internal units (requested {a1} rps)")
        print(f"Written V1 to {v1_int} internal units (requested {v1} rps)")
        print(f"Written AMAX to {amax_int} internal units (requested {amax} rps)")
        print(f"Written VMAX to {vmax_int} internal units (requested {vmax} rps)")
        print(f"Written DMAX to {dmax_int} internal units (requested {dmax} rps)")
        print(f"Written D1 to {d1_int} internal units (requested {d1} rps)")
        print(f"Written VSTOP to {vstop_int} internal units (requested {vstop} rps)")

    def rotate_rps(self, rps_velocity):
        vmax_int = self.rps_velocity_to_internal_velocity(rps_velocity)
        self.tmc_motor.rotate(vmax_int)

    def rps_velocity_to_internal_velocity(self, rps_velocity):
        """
        First convert rps to microstep : Vmicro = Vrps / microsteps_per_turn.
        Then convert to internal units, see datasheet page 81 for calculation.
        """
        mpt = self.microsteps * self.steps_per_turn  # Microsteps per turn number
        microstep_velocity = rps_velocity * mpt
        return int(microstep_velocity / (self.ckl_freq / 2 / (1 << 23)))

    def rps_acceleration_to_internal_acceleration(self, rps_acceleration):
        mpt = self.microsteps + self.steps_per_turn  # Microsteps per turn number
        microstep_acceleration = rps_acceleration * mpt
        return int((microstep_acceleration * (1 << 24) * 512 * 256) / (self.ckl_freq * self.ckl_freq))
