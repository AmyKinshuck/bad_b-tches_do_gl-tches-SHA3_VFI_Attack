'''  IMPORTS  '''

from machine import UART, Pin
import utime
import rp2
import random
import sys
import gc

# =====================================================================
#  Control Pi -> Victim Pi   (only the pins used in code; off-board)
# =====================================================================
#   Label            GP#  Pin    |D| Victim connection             |
# ------------------ --- ------- +-+-------------------------------+
GP_UART0_TX        = 12 # Pin 16 |O| -> Victim RX   (GP13, pin 17) |
GP_UART0_RX        = 13 # Pin 17 |I| <- Victim TX   (GP12, pin 16) |
GP_VICTIM_PWR      = 20 # Pin 26 |O| -> Victim 3V3_EN     (pin 37) |
GP_GLITCH          = 21 # Pin 27 |O| -> crowbar -> Victim TP7 (1V1)|
GP_VICTIM_RUN      = 22 # Pin 29 |O| -> Victim RUN        (pin 30) |
GP_PICO_LED        = 25 # OnPico |O|    Control onboard LED        |
GP_VICTIM_TRIG     = 26 # Pin 31 |I| <- Victim trigger    (pin 31) |
GP_EXT_TRIGGER_OUT = 28 # Pin 34 |O|    scope trigger out (J12)    |
# ------------------ --- ------- +-+-------------------------------+

# ==============================================================
# Default jumper settings: * indicates fitted jumper.
# ==============================================================
# J2 Left side of Victim Pico. (Left side is odd header pins numbers, right side is even):
# ==============================================================
#  J2.1-2:   "GP0" Do not fit
#  J2.3-4:   "GP1" Do not fit
# *J2.5-6:   "GND" Fit Jumper
#  J2.7-8:   "GP2" Do not fit
#  J2.9-10:  "GP3" Do not fit
# ____________________________
#  J2.11-12: "GP4" Do not fit
#  J2.13-14: "GP5" Do not fit
# *J2.15-16: "GND" Fit Jumper
#  J2.17-18: "GP6" Do not fit
#  J2.19-20: "GP7" Do not fit
# ____________________________
#  J2.21-22: "GP8"  Do not fit
#  J2.23-24: "GP9"  Do not fit
# *J2.25-26: "GND"  Fit Jumper
#  J2.27-28: "GP10" Do not fit
#  J2.29-30: "GP11" Do not fit
# ____________________________
# *J2.31-32: "GP12" Fit Jumper (Connects Victim UART0 Tx to Control UART0 Rx)
# *J2.33-34: "GP13" Fit Jumper (Connects Victim UART0 Rx to Control UART0 Tx)
# *J2.35-36: "GND"  Fit Jumper
# *J2.37-38: "GP14" Fit Jumper (GP14 Red LED)
# *J2.39-40: "GP15" Fit Jumper (GP15 Green LED)
# ___________________________________________________________________________
# 
# ============================================================================
# J8 (Left side is odd header pins numbers, right side is even):
# ============================================================================
#  J8.1-2:   "VBUS"     Do not fit
# *J8.3-4:   "VSYS"     Fit Jumper (Connects Victim VSYS to Control VSYS, via VSYS Bridge Jumper)
# *J8.5-6:   "GND"      Fit Jumper
# *J8.7-8:   "3V3_EN"   Fit Jumper (Connects Control GP20, via J1, to Victim 3V3_EN)
#  J8.9-10:  "3V3"      Do not fit
# ____________________________
#  J8.11-12: "ADC_VREF" Do not fit 
#  J8.13-14: "GP28"     Do not fit
# *J8.15-16: "AGND"     Fit Jumper
#  J8.17-18: "GP27"     Do not fit
# *J8.19-20: "GP26"     Fit Jumper (Victim Trigger, connects Victim GP26 to Control GP26)
# ____________________________
# *J8.21-22: "RUN"      Fit jumper (Connects Control GP22 to Victim RUN)
#  J8.23-24: "GP22"     Do not fit
# *J8.25-26: "GND"      Fit jumper
#  J8.27-28: "GP21"     Do not fit
#  J8.29-30: "GP20"     Do not fit
# ____________________________
#  J8.31-32: "GP19"     Do not fit
#  J8.33-34: "GP18"     Do not fit
# *J8.35-36: "GND"      Fit jumper
#  J8.37-38: "GP17"     Do not fit
# *J8.39-40: "GP16"     Fit jumper (Connects Victim GP16 to Blue LED)
# ============================================================================
# Other Jumpers
# ============================================================================
# *J1: "3V3 EN"        Fit after programming Victim (Connects Control GP20 to Victim )
# *J3  "Reset Control" Fit Jumper (Connects Control GP22 to Victim RUN)                                                                                                                                      
# *J4: "VSYS Bridge"   Fit Jumper (Connects Control VSYS to Victim VSYS)
# *J6: "J6"            Fit Jumper (Connects MOSFET output to pad on back of PCB, which should be connected to Victim TP7)


'''  UART CONFIGURATION  '''

# UART1 = Control <-> Host PC
UART1_BAUD_RATE = 115200
UART1_DATA_BITS = 8
UART1_PARITY    = None
UART1_STOP_BITS = 1

# UART0 = Control <-> Victim
UART0_BAUD_RATE = 115200
UART0_DATA_BITS = 8
UART0_PARITY    = None
UART0_STOP_BITS = 1


'''  HARDWARE INITIALISATION  '''

# Status LED
PICO_LED = Pin(GP_PICO_LED, Pin.OUT)

# Control pins to the Victim
EXT_TRIGGER_OUT = Pin(GP_EXT_TRIGGER_OUT, Pin.OUT, value = 0)
GLITCH = Pin(GP_GLITCH, Pin.OUT, value = 0)
# Define Victim reset
VICTIM_RUN = Pin(GP_VICTIM_RUN, Pin.OUT)  
# Hold Victim in reset
VICTIM_RUN.value(0)    
# Define Victim 3V3_EN
VICTIM_PWR = Pin(GP_VICTIM_PWR, Pin.OUT) 
# Power off Victim
VICTIM_PWR.value(0)                         

# UART0 to communicate with the victim
uart0 = UART(0, baudrate=UART0_BAUD_RATE, tx=Pin(GP_UART0_TX), rx=Pin(GP_UART0_RX), bits=UART0_DATA_BITS, parity=UART0_PARITY, stop=UART0_STOP_BITS)


'''  STATE & TIMING  '''

StateMachineStatus=[0] * 12
SM0 = None
ClockFreq_MHz = 150.0
ClockDuration_ns = 1/ClockFreq_MHz*1000
MinimumDelayOffset_ns = 40                  # fixed PIO setup offset
MinimumDelayOffset_clocks = round(MinimumDelayOffset_ns/ClockDuration_ns)
GlitchLength_clocks = 30
GlitchDelay_ns = 61953
GlitchLength_ns = 513
GlitchDelay_clocks = round((GlitchDelay_ns-MinimumDelayOffset_ns)/ClockDuration_ns)
InputTriggerLevel = 0                       # 0 = fire on H->L trigger
GlitchOutputLevel = 1                       # 1 = drive glitch pin high
GlitchFired = False
LastException = None
LastExceptionTime = None
VictimReadData = bytearray()


'''  SCAN PARAMETERS (ns)  '''

# These are the initial values I have setup, but these should be changed depending on the parameters you would like to invetsigate 

GlitchDelayMin = 40
GlitchDelayMax = 462000
GlitchLengthMin = 750
GlitchLengthMax = 900


'''  KNOWN RESPONSES  '''

# Correct SHA3-512 digest of the fixed input
ExpectedResp = bytes.fromhex("8AC8AFF5172D80E7F737A5FC53475A4806F6AF2011EFAC3AB0C18511E6DD758186AE79E6051B3DF29EF2EB3D6C99687DFAD14904F9BF54F68ACD5C4AD7AE6BC4")

# Specific faulted outputs that classify as "red" according to the reserach paper
RedCase1 = bytes.fromhex("ad56c35cab5063b9e7ea568314ec81c40ba577aae630de902004009e88f18da57bbdfdaaa0fc189c66c8d853248b6b118844d53f7d0ba11de0f3bfaf4cdd9b3f")
RedCase2 = bytes.fromhex("e7dde140798f25f18a47c033f9ccd584eea95aa61e2698d54d49806f304715bd57d05362054e288bd46f8e7f2da497ffc44746a4a0e5fe90762e19d60cda5b8c")
RedCase3 = bytes.fromhex("00010203040506070809101112131415161718192021222324252627282930310600000000000000000000000000000000000000000000000000000000000000")

# New red value that I found
RedCase4 = bytes.fromhex("30303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030")  # all-'0' fill


'''  PIO GLITCH PROGRAM  '''

# Wait for trigger H->L, then drive a timed high pulse after a delay.
# (set_init/sideset_init single values claim only GLITCH + EXT_TRIGGER_OUT)    
# Define a PIO function for waiting for input trigger H->L.

@rp2.asm_pio(set_init=(rp2.PIO.OUT_LOW), sideset_init=(rp2.PIO.OUT_LOW))
def HighGlitchOutputOnHighToLowTriggerInput():

    # High pulse, so set the output pin low initially
    set(pins, 0)        .side(0)

    # Wait for the TX FIFO word holding the output length (cycles),
    # then pull it into osr.
    pull(ifempty, block)         # FIFO=length,  osr=length

    # Store the length in x
    out(x, 32)                   # osr=length,   x=length
    jmp(x_dec, "lp_decrement_x") # subtract one: x=length-1
    label("lp_decrement_x")

    # Save length-1 in isr. Moving it to isr and back lets later
    # loops restore the value each pass.
    mov(isr, x)                  # x=length-1,   isr=length-1

    # Wait for the TX FIFO word holding the trigger delay (cycles),
    # then pull it into osr.
    pull(ifempty, block)         # osr=delay,    isr=length-1

    # Loop point while still armed
    wrap_target()

    # Copy the trigger delay from osr into y
    out(y, 32)                   # y=delay

    # Copy it back into osr for the next round
    mov(osr, y)

    # Restore length-1 into x (needed for all but the first loop)
    mov(x, isr)                  # x=length-1

    # Wait for the input trigger pin to be high
    wait(polarity=1, src=pin, index=0)

    # Then wait for the input trigger pin to go low
    wait(polarity=0, src=pin, index=0)

    # Trigger delay: hold for y cycles
    label("lp_y_loop_here")
    jmp(y_dec, "lp_y_loop_here") # y-- until 0

    # Drive the glitch pin high for x+1 cycles
    set(pins, 1)          .side(1)
    label("lp_x_loop_here")
    jmp(x_dec, "lp_x_loop_here") # x-- until 0

    # One more cycle to set the pin low again
    set(pins, 0)          .side(0)

    # Raise an interrupt to signal the glitch was actioned
    irq(rel(0))

    # Wait for the input trigger to go high again;
    # !!! note RP2350-E9 errata
    # may require an additional external pull-down resistor !!!
    # https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf Appendix E: Errata
    wait(polarity=1, src=pin, index=0)
    label("stop_here")
    jmp("stop_here")


'''  VICTIM CONTROL FUNCTIONS  '''

def HoldVictimReset(hold):
    if hold == 1:
        # Hold victim in reset
        VICTIM_RUN.value(0)                  
    elif hold == 0:
        # Release victim from reset
        VICTIM_RUN.value(1)                    

def ControlVictimPower(power=1):
    if power == 1:
        # Power victim on
        VICTIM_PWR.value(1)                    
    elif power == 0:
        # Power victim off
        VICTIM_PWR.value(0)                    

def PowerCycleVictim():
    # Power victim off
    VICTIM_PWR.value(0) 
    # Hold victim in reset
    HoldVictimReset(1)
    utime.sleep_ms(25)
    # Power victim on
    VICTIM_PWR.value(1)                         
    utime.sleep_ms(10)


'''  UART READ  '''

def ReadTargetBytesIntoBuffer(MaximumBufferSize = 1024, PrintNewData = False):
    global VictimReadData
    # Cap the number of read attempts so we never get stuck in a read
    MaxReads = 10
    while MaxReads and uart0.any():
        MaxReads -=1
        # Only read if the waiting data will fit in the buffer
        if len(VictimReadData)+uart0.any() < MaximumBufferSize:
            # Read everything currently waiting
            NewData = uart0.read(uart0.any())
            # Append it to the buffer
            VictimReadData.extend(NewData)
    return (len(VictimReadData), uart0.any())


'''  GLITCH ENGINE  '''

def DeactivateStateMachine(sm):
    # Deactivate state machine 0
    sm.active(0)

def GlitchedCallback(sm):
    global uart0
    global VictimReadData
    global GlitchFired
    # Turn off SM0
    # This avoids re-triggering before we have processed the glitch
    sm.active(0)           
    # Set the GlitchFired flag to True so we know a glitch has been fired                    
    GlitchFired = True                         

def Arm(ReplyLevel=1):
    global SM0, StateMachineStatus
    global GlitchDelay_clocks, GlitchLength_clocks
    global EXT_TRIGGER_OUT, GLITCH, VICTIM_TRIG
    global InputTriggerLevel, GlitchOutputLevel

    # Clear any previous arming state
    DeactivateStateMachine(rp2.StateMachine(0))
    if SM0 is not None:
        SM0.active(0)
        MyPIO=rp2.PIO(0)
        MyPIO.remove_program()

    # Trigger input - pulled up (victim drives it low to fire)
    VICTIM_TRIG = Pin(GP_VICTIM_TRIG, Pin.IN, Pin.PULL_UP)

    # Initialise outputs low before arming
    EXT_TRIGGER_OUT = Pin(GP_EXT_TRIGGER_OUT, Pin.OUT, Pin.PULL_DOWN)
    EXT_TRIGGER_OUT.value(0)
    GLITCH = Pin(GP_GLITCH, Pin.OUT, Pin.PULL_DOWN)
    GLITCH.value(0)

    # Build SM0: GLITCH = set pin, EXT_TRIGGER_OUT = sideset, VICTIM_TRIG = input
    SM0 = rp2.StateMachine(0, HighGlitchOutputOnHighToLowTriggerInput, set_base=GLITCH, in_base=VICTIM_TRIG, sideset_base=EXT_TRIGGER_OUT)
    SM0.irq(GlitchedCallback)
    # Load glitch length
    SM0.put(GlitchLength_clocks)     
    # Load glitch delay          
    SM0.put(GlitchDelay_clocks)      
    # Arm device           
    SM0.active(1)                               
    StateMachineStatus[0] = 1

def SetGlitchDelay(ns):
    global GlitchDelay_clocks
    GlitchDelay_clocks = round((ns - MinimumDelayOffset_ns) / ClockDuration_ns)

def SetGlitchLength(ns):
    global GlitchLength_clocks
    GlitchLength_clocks = round(ns / ClockDuration_ns)


'''  RESULT CLASSIFICATION  '''

def ClassifyData(hashoutput):
    classification = "gray"
    if len(hashoutput) == 0:
        classification = "gray"
        return classification
    SizedOutput = hashoutput[:64]
    if SizedOutput == ExpectedResp:
        classification = "green"
    elif SizedOutput == RedCase1:
        classification = "red"
    elif SizedOutput == RedCase2:
        classification = "red"
    elif SizedOutput == RedCase3:
        classification = "red"
    elif SizedOutput == RedCase4:
        classification = "red"
    else:
        classification = "cyan"
    return classification

def WriteResultsToHostPC(colour, delay_ns, length_ns, hashoutput):
    line = "%s,%d,%d,%s" % (colour, delay_ns, length_ns, hashoutput[:64].hex())
    # Send to host over USB
    print(line)                                


'''  GLITCHING  '''

def SingleGlitch():
    global GlitchFired

    # Turn onboard Control LED on for this glitch
    PICO_LED.value(1)

    # Clear buffer which result will be stored in
    VictimReadData[:] = b''
    # Set Glitch Fired flag to false
    GlitchFired = False
    
    # Power Victim Pi
    ControlVictimPower(1)
    # Hold Victim Pi in Reset
    HoldVictimReset(1)                          
    # Sleep to ensure Victim Pi is set up properly
    utime.sleep_ms(10)
                        
    # Arm Control Pi so it is ready to glitch
    Arm()                              
        
    # Flush UART to clear for the glitch output
    while uart0.any(): uart0.read() 
        
    # Release Victim Pi from reset
    HoldVictimReset(0)                          
    # Sleep to allow hash process to run and output the result
    utime.sleep_ms(30)                          
    # Read the output of the hash
    ReadTargetBytesIntoBuffer(MaximumBufferSize = 1024, PrintNewData = False)
    # Hold Victim Pi in reset again
    HoldVictimReset(1)                          

    # Turn onboard LED off to indicate glitch has finished
    PICO_LED.value(0)
                        
    return GlitchFired, bytes(VictimReadData)
  

def WideScan(attempts):
    global Results
    
    # Initialise a 
    Results = {"green":0, "red":0, "cyan":0, "gray":0, "NoGlitchFired":0}

    try:

        # Set a random glitch delay and length for a single attempt
        # Carry out the single glitch
        for i in range(attempts):
            GlitchDelay  = random.randint(GlitchDelayMin, GlitchDelayMax)
            GlitchLength = random.randint(GlitchLengthMin, GlitchLengthMax)
            SetGlitchDelay(GlitchDelay)
            SetGlitchLength(GlitchLength)
            GlitchFired_Flag, SHA3HashOutput = SingleGlitch()

            # Check the glitch fired
            # If it didn't then reset the victim
            if GlitchFired_Flag != True:
                Results["NoGlitchFired"] += 1
                PowerCycleVictim()
            else:
                # if glitch fired, classify the output
                Colour = ClassifyData(SHA3HashOutput)
                Results[Colour] += 1
                WriteResultsToHostPC(Colour, GlitchDelay, GlitchLength, SHA3HashOutput)

    except KeyboardInterrupt:
        print("\nStopped early at attempt", i)

    print("Capture Finished", Results)
    return Results

# Host PC will wait for the following command
print("READY")  

''' TEST A SINGLE GLITCH '''
# GlitchFired, Result = SingleGlitch()
# print(Result[:64].hex())

while True:
    command = sys.stdin.readline().strip()

    if command.startswith("scan"):
        parts = command.split()
        n = int(parts[1]) if len(parts) > 1 else 1000
        WideScan(n)
        print("DONE")

    elif command == "single":
        fired, data = SingleGlitch()
        print("fired", fired, "| class", ClassifyData(data), "|", data[:64].hex())
        print("DONE")

