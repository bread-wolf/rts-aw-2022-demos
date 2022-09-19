import pytrinamic
from pytrinamic.connections import ConnectionManager
from pytrinamic.evalboards import TMC5160_eval


class Tmc5160Config:
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

    def config_ramper(self, vstart=0.05, a1=10.0, v1=0.7, amax=7.0, vmax=1.5, dmax=7.0, d1=10.0, vstop=0.05):
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

        self.tmc_eval.write_register(self.tmc_ic.REG.A1, 1000)
        self.tmc_eval.write_register(self.tmc_ic.REG.V1, 50000)
        self.tmc_eval.write_register(self.tmc_ic.REG.D1, 500)
        self.tmc_eval.write_register(self.tmc_ic.REG.DMAX, 500)
        self.tmc_eval.write_register(self.tmc_ic.REG.VSTART, 0)
        self.tmc_eval.write_register(self.tmc_ic.REG.VSTOP, 10)
        self.tmc_eval.write_register(self.tmc_ic.REG.AMAX, 1000)

    def rps_velocity_to_internal_velocity(self, rps_velocity):
        """
        First convert rps to microstep : Vmicro = Vrps / microsteps_per_turn.
        Then convert to internal units, see datasheet page 81 for calculation.
        """
        mps = self.microsteps + self.steps_per_turn  # Microsteps per turn number
        microstep_velocity = rps_velocity / mps
        return microstep_velocity / (self.ckl_freq / 2 / (1 << 23))

    def rps_acceleration_to_internal_acceleration(self, rps_acceleration):
        mps = self.microsteps + self.steps_per_turn  # Microsteps per turn number
        microstep_acceleration = rps_acceleration / mps
        return (microstep_acceleration * (1 << 24) * 512 * 256) / (self.ckl_freq * self.ckl_freq)
