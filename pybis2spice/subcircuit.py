# ----------------------------------------------------------------------------
# Author: Kishan Amratia
# Module Name: subcircuit.py
#
# Module Description:
# Companion functions for the pybis2spice module to create the SPICE subcircuit file
#
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import os.path

import numpy as np
import pybis2spice
import version


_TIME = 0
_KU = 1
_KD = 2
_KD_OD = 1


def generate_spice_model(io_type, subcircuit_type, ibis_data, corner, output_filepath):
    """
    Wrapper around the subcircuit file creation functions. Calls the relevant function i.e. LTSpice or Generic

        Parameters:
            io_type - "Input" or "Output"
            subcircuit_type - "LTSpice" or "Generic"
            ibis_data - a DataModel object (defined in pybis2spice.py)
            corner - "WeakSlow" or "Typical" or "FastStrong"
            output_filepath - path of output file

        Returns:
            The path of the created file
    """
    ret = None
    if io_type == "Output":

        if subcircuit_type == "Generic":
            ret = create_generic_output_model(ibis_data, corner, io_type, output_filepath)

        if subcircuit_type == "LTSpice":
            ret = create_ltspice_output_model(ibis_data, corner, io_type, output_filepath)

    if io_type == "Input":
        ret = create_input_model(ibis_data, corner, io_type, output_filepath)

    return ret


def convert_corner_str_to_index(corner):
    """
    Coverts the corner string into an index number used to reference the arrays within pybis2spice methods
    Parameters:
        corner - "Typical", "WeakSlow" or "FastStrong"

    Returns:
        index - 0, 1, 2 corresponding to the corner string "Typical", "WeakSlow" and "FastStrong" respectively
    """
    index = 0
    if corner == "Typical":
        index = 0
    if corner == "WeakSlow":
        index = 1
    if corner == "FastStrong":
        index = 2

    return index


def spice_header_info(ibis_data, corner, extra_info=""):
    """
    Returns a header string for the ibis file. Helps create a comment on the SPICE subcircuit file

    Parameters:
        ibis_data - a DataModel object (defined in pybis2spice.py)
        corner - "Typical", "WeakSlow" or "FastStrong"
    """
    st = "*********************************************************************\n*\n"
    st += f'* IBIS filename: {ibis_data.file_name}\n'
    st += f'* Component: {ibis_data.component_name}\n'
    st += f'* Model: {ibis_data.model_name}\n'
    st += f'* Model Type: {ibis_data.model_type}\n'
    st += f'* Corner: {corner}\n'
    st += f'* Voltage Range (V): {ibis_data.v_range} (Typ, Min, Max)\n'
    st += f'* Temperature Range (degC): {ibis_data.temp_range} (Typ, Min, Max)\n'
    st += f'* SPICE subcircuit model created with pybis2spice version {version.get_version()}\n'
    st += f'* For more info, visit https://github.com/kamratia1/pybis2spice/\n*\n'
    st += f'{extra_info}'
    st += "*********************************************************************\n\n"
    return st


def spice_rlc_netlist(ibis_data, corner, pin_name):
    """
    Returns a netlist string for the r_pkg, l_pkg,  c_comp

    Parameters:
        ibis_data - a DataModel object (defined in pybis2spice.py)
        corner - "Typical", "WeakSlow" or "FastStrong"
    """
    _INDEX = convert_corner_str_to_index(corner)
    c_pkg = ibis_data.c_pkg[_INDEX]
    l_pkg = ibis_data.l_pkg[_INDEX]
    r_pkg = ibis_data.r_pkg[_INDEX]
    st = ""

    if c_pkg is None:
        st += f'.param C_pkg = {ibis_data.c_pkg[0]}\n'
        st += f'* WARNING: The IBIS model does not have a value for the C_pkg for the {corner} corner, ' \
              f'therefore this has been set to the typical value for C_pkg\n'
    elif c_pkg == 0:
        st += f'.param C_pkg = 0.1e-12\n'
        st += f'* WARNING: Could not parse the C_pkg so has been set to a nominal of 0.1pF\n'
    else:
        st += f'.param C_pkg = {c_pkg}\n'

    if l_pkg is None:
        st += f'.param L_pkg = {ibis_data.l_pkg[0]}\n'
        st += f'* WARNING: The IBIS model does not have a value for the L_pkg for the {corner} corner, ' \
              f'therefore this has been set to the typical value for L_pkg\n'
    elif l_pkg == 0:
        st += f'.param L_pkg = 1e-9\n'
        st += f'* WARNING: Could not parse the L_pkg so has been set to a nominal of 1nF\n'
    else:
        st += f'.param L_pkg = {l_pkg}\n'

    if r_pkg is None:
        st += f'.param R_pkg = {ibis_data.r_pkg[0]}\n'
        st += f'* WARNING: The IBIS model does not have a value for the R_pkg for the {corner} corner, ' \
              f'therefore this has been set to the typical value for R_pkg\n'
    elif r_pkg == 0:
        st += f'.param R_pkg = 0.01\n'
        st += f'* WARNING: Could not parse the R_pkg so has been set to a nominal of 0.01ohm\n'
    else:
        st += f'.param R_pkg = {r_pkg}\n'

    st += f'.param C_comp = {ibis_data.c_comp[_INDEX]}\n\n'

    st += f'R1 {pin_name} MID {{R_pkg}}\n'
    st += f'L1 DIE MID {{L_pkg}}\n'
    st += f'C1 {pin_name} 0 {{C_pkg}}\n'
    st += f'C2 DIE 0 {{C_comp}}\n\n'

    return st


def define_pwr_and_gnd_clamps(ibis_data, corner):
    """
    Arbitrary Source definition for power and ground clamp
    Parameters:
        ibis_data - a DataModel object (defined in pybis2spice.py)
        corner - "Typical", "WeakSlow" or "FastStrong"

    Returns the netlist for the arbitrary source
    """

    _INDEX = convert_corner_str_to_index(corner)
    _CORNER_INDEX = _INDEX + 1

    pwr_clamp_ref = pybis2spice.get_reference(ibis_data.pwr_clamp_ref, ibis_data.v_range, _CORNER_INDEX)
    gnd_clamp_ref = pybis2spice.get_reference(ibis_data.gnd_clamp_ref, 0, _CORNER_INDEX)

    return_val = ""

    # Arbitrary Source definition for power and ground clamp
    if ibis_data.iv_pwr_clamp is not None:
        return_val += f'V1 PWR_CLAMP_REF 0 {pwr_clamp_ref}\n'
        pwr_clamp_table_str = convert_iv_table_to_str(np.flip(pwr_clamp_ref - ibis_data.iv_pwr_clamp[:, 0]),
                                                      np.flip(ibis_data.iv_pwr_clamp[:, _CORNER_INDEX]))
        return_val += f'B1 DIE PWR_CLAMP_REF I = table(V(DIE), {pwr_clamp_table_str})\n'

    if ibis_data.iv_gnd_clamp is not None:
        return_val += f'V2 GND_CLAMP_REF 0 {gnd_clamp_ref}\n'
        gnd_clamp_table_str = convert_iv_table_to_str(ibis_data.iv_gnd_clamp[:, 0] - gnd_clamp_ref,
                                                      ibis_data.iv_gnd_clamp[:, _CORNER_INDEX])
        return_val += f'B2 DIE GND_CLAMP_REF I = table(V(DIE), {gnd_clamp_table_str})\n\n'

    return return_val


def define_pullup_and_pulldown_devices(ibis_data, corner):
    """
    Arbitrary Source definition for pullup and pulldown devices
    Parameters:
        ibis_data - a DataModel object (defined in pybis2spice.py)
        corner - "Typical", "WeakSlow" or "FastStrong"

    Returns the netlist for the arbitrary source for the devices
    """

    _INDEX = convert_corner_str_to_index(corner)
    _CORNER_INDEX = _INDEX + 1

    pullup_ref = pybis2spice.get_reference(ibis_data.pullup_ref, ibis_data.v_range, _CORNER_INDEX)
    pulldown_ref = pybis2spice.get_reference(ibis_data.pulldown_ref, 0, _CORNER_INDEX)

    return_val = ""
    # Arbitrary Source definition for pullup and pulldown devices
    if ibis_data.iv_pullup is not None:
        return_val += f'V3 PULLUP_REF 0 {pullup_ref}\n'
        pullup_table_str = convert_iv_table_to_str(np.flip(pullup_ref - ibis_data.iv_pullup[:, 0]),
                                                   np.flip(ibis_data.iv_pullup[:, _CORNER_INDEX]))
        return_val += f'B3 DIE PULLUP_REF I={{V(Ku)*table(V(DIE), {pullup_table_str})}}\n'

    if ibis_data.iv_pulldown is not None:
        return_val += f'V4 PULLDOWN_REF 0 {pulldown_ref}\n'
        pulldown_table_str = convert_iv_table_to_str(ibis_data.iv_pulldown[:, 0] - pulldown_ref,
                                                     ibis_data.iv_pulldown[:, _CORNER_INDEX])
        return_val += f'B4 DIE PULLDOWN_REF I={{V(Kd)*table(V(DIE), {pulldown_table_str})}}\n\n'

    return return_val


def create_input_model(ibis_data, corner, io_type, output_filepath):
    """
    Creates a SPICE generic subcircuit model.
    Generic models are simple and only supports a single oscillation pulse with a given frequency

    Parameters:
        ibis_data - a DataModel object (defined in pybis2spice.py)
        corner - "Typical", "WeakSlow" or "FastStrong"
        io_type - "Input" or "Output"
        output_filepath - path of output file
    """

    with open(output_filepath, 'w') as file:

        header = spice_header_info(ibis_data, corner)
        file.write(header)

        file.write(f'.SUBCKT {ibis_data.model_name}-{io_type}-{corner} IN\n\n')

        rlc_netlist = spice_rlc_netlist(ibis_data, corner, pin_name="IN")
        file.write(rlc_netlist)

        clamps_netlist = define_pwr_and_gnd_clamps(ibis_data, corner)
        file.write(clamps_netlist)

        file.write(f'.ENDS\n')

    return 0


def create_generic_output_model(ibis_data, corner, io_type, output_filepath):
    """
    Creates a SPICE generic subcircuit model.
    Generic models are simple and only supports a single oscillation pulse with a given frequency

    Parameters:
        ibis_data - a DataModel object (defined in pybis2spice.py)
        corner - "Typical", "WeakSlow" or "FastStrong"
        io_type - "Input" or "Output"
        k_param_rise - the k_parameter numpy array for the rising waveform (output of the solve_k_params_output method)
        k_param_fall - the k_parameter numpy array for the falling waveform (output of the solve_k_params_output method)
        output_filepath - path of output file

    Returns 0 if there are no errors in the creation
    """
    return_val = 0
    try:
        _INDEX = convert_corner_str_to_index(corner)
        _CORNER_INDEX = _INDEX + 1

        if ibis_data.model_type.lower() == "open_drain":
            kr = pybis2spice.solve_k_params_output_open_drain(ibis_data, corner=_CORNER_INDEX, waveform_type="Rising")
            kf = pybis2spice.solve_k_params_output_open_drain(ibis_data, corner=_CORNER_INDEX, waveform_type="Falling")
        else:
            kr = pybis2spice.solve_k_params_output(ibis_data, corner=_CORNER_INDEX, waveform_type="Rising")
            kf = pybis2spice.solve_k_params_output(ibis_data, corner=_CORNER_INDEX, waveform_type="Falling")

        kr = pybis2spice.compress_param(kr)
        kf = pybis2spice.compress_param(kf)

        with open(output_filepath, 'w') as file:
            header = spice_header_info(ibis_data, corner)
            file.write(header)

            file.write(f'.SUBCKT {ibis_data.model_name}-{io_type}-{corner} OUT params: freq=10Meg duty=0.5\n\n')

            rlc_netlist = spice_rlc_netlist(ibis_data, corner, pin_name="OUT")
            file.write(rlc_netlist)

            clamps_netlist = define_pwr_and_gnd_clamps(ibis_data, corner)
            file.write(clamps_netlist)

            device_netlist = define_pullup_and_pulldown_devices(ibis_data, corner)
            file.write(device_netlist)

            # Calculations to define the oscillation stimulus
            if ibis_data.model_type.lower() == "open_drain":
                k_d_osc_str = create_osc_waveform_pwl(kr[:, _TIME], kr[:, _KD_OD], kf[:, _TIME], kf[:, _KD_OD])
            else:
                k_u_osc_str = create_osc_waveform_pwl(kr[:, _TIME], kr[:, _KU], kf[:, _TIME], kf[:, _KU])
                k_d_osc_str = create_osc_waveform_pwl(kr[:, _TIME], kr[:, _KD], kf[:, _TIME], kf[:, _KD])

            (offset_neg_r, offset_pos_r) = determine_crossover_offsets(kr)
            (offset_neg_f, offset_pos_f) = determine_crossover_offsets(kf)

            file.write(f'* Define Oscillation Sources\n')
            file.write(f'.param calc_gap_pos = {{(duty/freq) - {offset_pos_r} - {offset_neg_f}}}\n')
            file.write(f'.param calc_gap_neg = {{((1-duty)/freq) - {offset_pos_f} - {offset_neg_r}}}\n\n')

            file.write(f'.param GAP_POS = {{if(calc_gap_pos <= 0, 0.1e-12, calc_gap_pos)}}\n')
            file.write(f'.param GAP_NEG = {{if(calc_gap_neg <= 0, 0.1e-12, calc_gap_neg)}}\n\n')

            if ibis_data.model_type.lower() != "open_drain":
                file.write(f'V5 Ku 0 PWL({k_u_osc_str})\n\n')

            file.write(f'V6 Kd 0 PWL({k_d_osc_str})\n\n')

            file.write(f'.ENDS\n')
    except:
        return_val = 1

    return return_val


def ltspice_stimulus_netlist_setup():
    """
    Returns a netlist string that sets up the LTSpice stimulus sources for the model
    """
    # Setup the Stimulus setting options for the Pullup Waveform (Ku)
    setup_str = ".model SW SW(Ron=1n Roff=1G Vt=.5 Vh=-.4)\n\n"
    setup_str += "\n* Setup the Stimulus setting options for the Pullup Waveform (Ku)\n"
    setup_str += "V10 OSC 0 {if(stimulus_==1, 1, 0)}\n"
    setup_str += "V11 OSC_INV 0 {if(stimulus_==2, 1, 0)}\n"
    setup_str += "V12 RISE 0 {if(stimulus_==3, 1, 0)}\n"
    setup_str += "V13 FALL 0 {if(stimulus_==4, 1, 0)}\n"
    setup_str += "V14 HIGH 0 {if(stimulus_==5, 1, 0)}\n"
    setup_str += "V15 LOW 0 {if(stimulus_==6, 1, 0)}\n"
    setup_str += "S1 Ku K_U_OSC OSC 0 SW\n"
    setup_str += "S2 Ku K_U_OSC_INV OSC_INV 0 SW\n"
    setup_str += "S3 Ku K_U_RISE RISE 0 SW\n"
    setup_str += "S4 Ku K_U_FALL FALL 0 SW\n"
    setup_str += "S5 Ku K_U_HIGH HIGH 0 SW\n"
    setup_str += "S6 Ku K_U_LOW LOW 0 SW\n"

    # Setup the Stimulus setting options for the Pulldown Waveform (Kd)
    setup_str += "\n* Setup the Stimulus setting options for the Pulldown Waveform (Kd)\n"
    setup_str += "S7 Kd K_D_OSC OSC 0 SW\n"
    setup_str += "S8 Kd K_D_OSC_INV OSC_INV 0 SW\n"
    setup_str += "S9 Kd K_D_RISE RISE 0 SW\n"
    setup_str += "S10 Kd K_D_FALL FALL 0 SW\n"
    setup_str += "S11 Kd K_D_HIGH HIGH 0 SW\n"
    setup_str += "S12 Kd K_D_LOW LOW 0 SW\n"

    return setup_str


def create_ltspice_output_model(ibis_data, corner, io_type, output_filepath):
    """
    Creates a SPICE subcircuit model designed for LTSpice.
    LTSpice specific models provide extra functionality to manipulate the waveform stimulus of the output

    Parameters:
        ibis_data - a DataModel object (defined in pybis2spice.py)
        corner - "Typical", "WeakSlow" or "FastStrong"
        io_type - "Input" or "Output"
        output_filepath - path of output file

    Returns 0 if there are no errors in the creation
    """

    return_val = 0
    try:
        _INDEX = convert_corner_str_to_index(corner)
        _CORNER_INDEX = _INDEX + 1

        if ibis_data.model_type.lower() == "open_drain":
            kr = pybis2spice.solve_k_params_output_open_drain(ibis_data, corner=_CORNER_INDEX, waveform_type="Rising")
            kf = pybis2spice.solve_k_params_output_open_drain(ibis_data, corner=_CORNER_INDEX, waveform_type="Falling")
        else:
            kr = pybis2spice.solve_k_params_output(ibis_data, corner=_CORNER_INDEX, waveform_type="Rising")
            kf = pybis2spice.solve_k_params_output(ibis_data, corner=_CORNER_INDEX, waveform_type="Falling")

        kr = pybis2spice.compress_param(kr)
        kf = pybis2spice.compress_param(kf)

        with open(output_filepath, 'w') as file:

            parameter_info = "* Note: This model may only work in LTSpice.\n"
            parameter_info += "* Stimulus Options: \n" \
                              "*\t1 - Oscillate at given freq and duty\n" \
                              "*\t2 - Inverted Oscillate at given freq and duty\n" \
                              "*\t3 - Rising Edge with delay\n" \
                              "*\t4 - Falling Edge with delay\n" \
                              "*\t5 - Stuck High\n" \
                              "*\t6 - Stuck Low\n" \
                              "*\t7 - HighZ (if 3-State output)\n\n"
            header = spice_header_info(ibis_data, corner, extra_info=parameter_info)
            file.write(header)

            subcircuit = f'.SUBCKT {ibis_data.model_name}-{io_type}-{corner} '
            subcircuit_params = f'OUT params: stimulus=1 freq=10Meg duty=0.5 delay=0 \n\n'

            file.write(subcircuit + subcircuit_params)

            rlc_netlist = spice_rlc_netlist(ibis_data, corner, pin_name="OUT")
            file.write(rlc_netlist)

            clamps_netlist = define_pwr_and_gnd_clamps(ibis_data, corner)
            file.write(clamps_netlist)

            device_netlist = define_pullup_and_pulldown_devices(ibis_data, corner)
            file.write(device_netlist)

            stimulus_netlist = ltspice_stimulus_netlist_setup() # Look at this in more detail
            file.write(stimulus_netlist)

            (offset_neg_r, offset_pos_r) = determine_crossover_offsets(kr)
            (offset_neg_f, offset_pos_f) = determine_crossover_offsets(kf)

            # Calculations for defining the frequency and duty cycle of the oscillation stimuli'
            file.write(f'\n* Define Oscillation Sources\n')
            file.write(f'.param calc_gap_pos = {{(duty/freq) - {offset_pos_r} - {offset_neg_f}}}\n')
            file.write(f'.param calc_gap_neg = {{((1-duty)/freq) - {offset_pos_f} - {offset_neg_r}}}\n\n')
            file.write(f'.param GAP_POS = {{if(calc_gap_pos <= 0, 0.1e-12, calc_gap_pos)}}\n')
            file.write(f'.param GAP_NEG = {{if(calc_gap_neg <= 0, 0.1e-12, calc_gap_neg)}}\n\n')

            max_stimulus = 6
            if ibis_data.model_type.lower() == "3-state":
                max_stimulus = 7

            # Limit the stimulus between 1 and 7
            file.write(f'.param stimulus_ = {{if(stimulus < 1, 1, '
                       f'if(stimulus > {max_stimulus}, {max_stimulus}, stimulus)}}\n\n')

            # Oscillation Strings
            if ibis_data.model_type.lower() == "open_drain":
                kd_osc_str = create_osc_waveform_pwl(kr[:, _TIME], kr[:, _KD_OD], kf[:, _TIME], kf[:, _KD_OD])
            else:
                ku_osc_str = create_osc_waveform_pwl(kr[:, _TIME], kr[:, _KU], kf[:, _TIME], kf[:, _KU])
                kd_osc_str = create_osc_waveform_pwl(kr[:, _TIME], kr[:, _KD], kf[:, _TIME], kf[:, _KD])

            if ibis_data.model_type.lower() == "open_drain":
                kd_inv_osc_str = create_osc_waveform_pwl(kf[:, _TIME], kf[:, _KD_OD], kr[:, _TIME], kr[:, _KD_OD])
            else:
                ku_inv_osc_str = create_osc_waveform_pwl(kf[:, _TIME], kf[:, _KU], kr[:, _TIME], kr[:, _KU])
                kd_inv_osc_str = create_osc_waveform_pwl(kf[:, _TIME], kf[:, _KD], kr[:, _TIME], kr[:, _KD])

            # Rising Edge Strings
            if ibis_data.model_type.lower() == "open_drain":
                kdr_str = create_edge_waveform_pwl(kr[:, _TIME], kr[:, _KD_OD])
            else:
                kur_str = create_edge_waveform_pwl(kr[:, _TIME], kr[:, _KU])
                kdr_str = create_edge_waveform_pwl(kr[:, _TIME], kr[:, _KD])

            # Falling Edge Strings
            if ibis_data.model_type.lower() == "open_drain":
                kdf_str = create_edge_waveform_pwl(kf[:, _TIME], kf[:, _KD_OD])
            else:
                kuf_str = create_edge_waveform_pwl(kf[:, _TIME], kf[:, _KU])
                kdf_str = create_edge_waveform_pwl(kf[:, _TIME], kf[:, _KD])

            if ibis_data.model_type.lower() != "open_drain":
                # Setup the K-Parameter waveforms for the Pullup transistor (Ku)
                file.write(f"V16 K_U_OSC 0 PWL REPEAT FOREVER ({ku_osc_str}) ENDREPEAT\n")
                file.write(f"V17 K_U_HIGH 0 1\n")
                file.write(f"V18 K_U_LOW 0 0\n")
                file.write(f"V19 K_U_OSC_INV 0 PWL REPEAT FOREVER ({ku_inv_osc_str}) ENDREPEAT\n")
                file.write(f"V20 K_U_RISE 0 PWL({kur_str})\n")
                file.write(f"V21 K_U_FALL 0 PWL({kuf_str})\n")

            # Setup the K-Parameter waveforms for the Pullup transistor (Kd)
            file.write(f"V36 K_D_OSC 0 PWL REPEAT FOREVER ({kd_osc_str}) ENDREPEAT\n")
            file.write(f"V37 K_D_HIGH 0 0\n")
            file.write(f"V38 K_D_LOW 0 1\n")
            file.write(f"V39 K_D_OSC_INV 0 PWL REPEAT FOREVER ({kd_inv_osc_str}) ENDREPEAT\n")
            file.write(f"V40 K_D_RISE 0 PWL({kdr_str})\n")
            file.write(f"V41 K_D_FALL 0 PWL({kdf_str})\n")

            if ibis_data.model_type.lower() == "3-state":
                file.write("V50 EN 0 {if(stimulus==7, 1, 0)}\n")
                file.write("S13 Ku 0 EN 0 SW\n")
                file.write("S14 Kd 0 EN 0 SW\n")

            file.write(f'\n.ENDS\n')
    except:
        return_val = 1

    return return_val


def create_ltspice_symbol(ibis_data, corner, model_path, io_type):
    """
    Creates an LTSpice symbol for the given model_path within the model_path directory
    This helps with the relative referencing of the model_path within the symbol file.
    The symbol is given the same name as the model for consistency.

    Parameters:
        ibis_data - a DataModel object (defined in pybis2spice.py)
        corner - "Typical", "WeakSlow" or "FastStrong"
        model_path - filepath of the subcircuit model
        io_type - "Input" or "Output"

    Returns the filepath of the created symbol
    """
    symbol_path = os.path.join(os.path.dirname(model_path), f'{ibis_data.model_name}-{io_type}-{corner}.asy')
    symbol_value = f'{ibis_data.model_name}-{io_type}-{corner}'
    model_filename = os.path.basename(model_path)

    with open(symbol_path, 'w') as file:
        if io_type == "Input":
            file.write(f"Version 4\n")
            file.write(f"SymbolType BLOCK\n")
            file.write(f"LINE Normal 0 32 48 64\n")
            file.write(f"LINE Normal 0 96 48 64\n")
            file.write(f"LINE Normal 0 96 0 32\n")
            file.write(f"WINDOW 0 8 16 Left 2\n")
            file.write(f"WINDOW 3 8 120 Left 2\n")
            file.write(f"SYMATTR Value {symbol_value}\n")
            file.write(f"SYMATTR Prefix X\n")
            file.write(f"SYMATTR ModelFile {model_filename}\n")
            file.write(f"PIN 0 64 NONE 0\n")
            file.write(f"PINATTR PinName IN\n")
            file.write(f"PINATTR SpiceOrder 1\n")

        if io_type == "Output":
            file.write(f"Version 4\n")
            file.write(f"SymbolType BLOCK\n")
            file.write(f"LINE Normal -16 0 32 -32\n")
            file.write(f"LINE Normal -16 -64 -16 0\n")
            file.write(f"LINE Normal 32 -32 -16 -64\n")
            file.write(f"WINDOW 0 0 -80 Bottom 2\n")
            file.write(f"WINDOW 3 8 24 Top 2\n")
            file.write(f"WINDOW 39 8 48 Top 2\n")
            file.write(f"SYMATTR Value {symbol_value}\n")
            file.write(f"SYMATTR SpiceLine stimulus=1 freq=10Meg duty=0.5 delay=0\n")
            file.write(f"SYMATTR Prefix X\n")
            file.write(f"SYMATTR ModelFile {model_filename}\n")
            file.write(f"PIN 32 -32 NONE 8\n")
            file.write(f"PINATTR PinName OUT\n")
            file.write(f"PINATTR SpiceOrder 1\n")

    return symbol_path


def convert_iv_table_to_str(voltage, current):
    """
    Creates the IV table of values for the current sources modelling the devices and clamps

        Parameters:
            voltage - numpy voltage array
            current - corresponding numpy current array

        Returns:
            str_val: the string that goes into subcircuit table
    """
    str_val = f'{voltage[0]}, {current[0]}'
    for i in range(1, len(voltage)):
        str_val = str_val + f', {voltage[i]}, {current[i]}'
    return str_val


def create_edge_waveform_pwl(time, k_param):
    """
    Creates the PWL value string for the oscillation waveform
    Only valid for LTSpice subcircuit

        Parameters:
            time - numpy time array for k parameter waveform
            k_param - numpy array for k_r or k_f waveform

        Returns:
            str_val: the string that goes into PWL source for the edge
    """
    str_val = f'{{delay}}, {k_param[0]}'
    for i in range(1, len(time)):
        str_val = str_val + f', {{delay+{time[i]}}}, {k_param[i]}'
    return str_val


def create_osc_waveform_pwl(t1, k1, t2, k2):
    """
    Creates the PWL value string for the oscillation waveform

        Parameters:
            t1 - numpy time array for first edge (rising or falling)
            t2 - numpy time array for second edge (rising or falling)
            k1 - numpy ku or kd array for first edge (rising or falling)
            k2 - numpy ku or kd array for second edge (rising or falling)

        Returns:
            str_val: the string that goes into the oscillator PWL source
    """

    # First Edge
    # the +0.01p fudge is for Simetrix as it seems to have a bug in its PWLS source
    # where it cannot start at any value other than 0 regardless of the k_r[0] value
    str_val = f'0 {k1[0]} +0.01e-12 {k1[0]}'
    for i in range(1, len(t1)):
        dt = t1[i] - t1[i - 1]
        str_val = str_val + f' +{dt} {k1[i]}'

    str_val = str_val + f' +{{GAP_POS}} {k1[-1]} +{t2[0]} {k2[0]}'

    # Second Edge
    for i in range(1, len(t2)):
        dt = t2[i] - t2[i - 1]
        str_val = str_val + f' +{dt} {k2[i]}'

    str_val = str_val + f' +{{GAP_NEG}} {k2[-1]}'

    # gap_pos and gap_neg are parameters calculated within SPICE to oscillate at the right frequency and duty
    return str_val


def determine_crossover_offsets(k_param):
    """
    returns the approximate crossover point between the rising and falling k_param waveforms
        offset_neg: Time offset between beginning of k_param to crossover point
        offset_neg: Time offset between crossover point to end of k_param
    """

    # crossover time point (x_t)
    if np.shape(k_param)[1] == 3:
        # Find the index of the minimum value of the difference between k_u and k_d
        index = np.argmin(np.absolute(k_param[:, 1] - k_param[:, 2]))
        x_t = k_param[index, 0]
    else:
        # Find the index of the value at the halfway voltage point of the k-param waveform
        index = np.argmin((np.max(k_param[:, 1]) - np.min(k_param[:, 1]))/2)
        x_t = k_param[index, 0]

    # Time offset
    offset_neg = x_t - k_param[0][0]
    offset_pos = k_param[:, 0][-1] - x_t

    return offset_neg, offset_pos
