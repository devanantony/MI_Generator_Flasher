import os
import sys
import zlib
import argparse
from struct import *
import configparser
import csv
from datetime import datetime

dir_path = os.path.dirname(os.path.realpath(__file__))

# Global Variable
Value_of_size_field = 0

# Get parent folder of the script
parent_folder = os.path.dirname(os.path.abspath(__file__))

# Create a folder with the current date (YYYYMMDD)
date_folder = datetime.now().strftime("%Y%m%d")
output_folder = os.path.join(parent_folder, date_folder)
os.makedirs(output_folder, exist_ok=True)  # ensure the folder exists

# Set the global file path inside the current date folder
global_file_path = os.path.join(output_folder, f"{date_folder}.txt")

VERSION_STRING = "v1.0"

MI_GLOBAL_HEADER = 'mi_global_header'
ME_CONTENT = 'me_content'
ME_CONTENT_DYNAMIC_1 = 'me_content_dynamic_1'
ME_CONTENT_DYNAMIC_2 = 'me_content_dynamic_2'

CM_CONTENT = 'cm_content'
OEM_CONTENT = 'oem_content'

MAX_RETRIES = 3
MAX_RETRIES_EXPIRED = 0

OEM_CONTENT_DYNAMIC_1 = 'oem_content_dynamic_1'
OEM_CONTENT_DYNAMIC_2 = 'oem_content_dynamic_2'

RESERVED_ME = 'reserved_ME'
RESERVED_CM = 'reserved_cm'
RESERVED_OEM = 'reserved_OEM'

def input_value_check(lstring, max_size, type):
    err_print = MAX_RETRIES
    while err_print:
        if lstring == "production_date":
            input_val = str(input('Enter {} in format[DDMMYYYY]({} byte {}): '.format(lstring, max_size, type)))
        else:
            input_val = str(input('Enter {} ({} byte {}): '.format(lstring, max_size, type)))

        if lstring == "brd_ver":
            int_val = int(input_val)
            if not (0 <= int_val <= 255):
                print("[Error] - {} must be in the range of [0 to 255]!".format(lstring))
                err_print -= 1
                if err_print == MAX_RETRIES_EXPIRED:
                    input_val = None
            else:
                err_print = MAX_RETRIES_EXPIRED
        else:
            if len(input_val) > max_size:
                print("[Error] - {} cannot exceed {} bytes!".format(lstring, max_size))
                err_print -= 1
                if err_print == MAX_RETRIES_EXPIRED:
                    input_val = None
            else:
                err_print = MAX_RETRIES_EXPIRED
    return input_val

def edit_mi_data(mi):
    for content in mi[ME_CONTENT_DYNAMIC_1]:
        content_val = input_value_check(content, int(mi[ME_CONTENT_DYNAMIC_1][content]), "string")
        if content_val is None:
            return "Max tries expired!"
        print("[INFO] - \t{} value entered {}".format(content, content_val))
        mi[ME_CONTENT_DYNAMIC_1][content] = content_val

    for content in mi[ME_CONTENT_DYNAMIC_2]:
        content_val = input_value_check(content, int(mi[ME_CONTENT_DYNAMIC_2][content]), "string")
        if content_val is None:
            return "Max tries expired!"
        print("[INFO] - \t{} value entered {}".format(content, content_val))
        mi[ME_CONTENT_DYNAMIC_2][content] = content_val

    mi[ME_CONTENT_DYNAMIC_2][RESERVED_ME] = "FFFFFFFF"

    for content in mi[CM_CONTENT]:
        content_val = input_value_check(content, int(mi[CM_CONTENT][content]), "string")
        with open(global_file_path, "a") as file:
            file.write(content_val + "\t")
        if content_val is None:
            return "Max tries expired!"
        print("[INFO] - \t{} value entered {}".format(content, content_val))
        mi[CM_CONTENT][content] = content_val

    for content in mi[OEM_CONTENT_DYNAMIC_1]:
        content_val = input_value_check(content, int(mi[OEM_CONTENT_DYNAMIC_1][content]), "string")
        with open(global_file_path, "a") as file:
            file.write(content_val + "\t")
        if content_val is None:
            return "Max tries expired!"
        print("[INFO] - \t{} value entered '{}'".format(content, content_val))
        mi[OEM_CONTENT_DYNAMIC_1][content] = content_val

    for content in mi[OEM_CONTENT_DYNAMIC_2]:
        content_val = input_value_check(content, int(mi[OEM_CONTENT_DYNAMIC_2][content]), "string")
        with open(global_file_path, "a") as file:
            file.write(content_val + "\n")
        if content_val is None:
            return "Max tries expired!"
        print("[INFO] - \t{} value entered '{}'".format(content, content_val))
        mi[OEM_CONTENT_DYNAMIC_2][content] = content_val

    mi[CM_CONTENT][RESERVED_CM] = 0
    mi[OEM_CONTENT_DYNAMIC_2][RESERVED_OEM] = 0
    return None

def writeAddrVal(val_list, output_bin):
    val = val_list.split(",")
    ret_array = []
    for _, addr_str in enumerate(val):
        addr = str2dec(str(addr_str))
        addr_el = pack('<B', addr)
        output_bin.write(addr_el)
        ret_array.append(addr)
    return ret_array

def str2dec(string):
    prefix = string[0:2]
    if prefix == "0X" or prefix == "0x":
        dec = int(string[2:], 16)
    else:
        dec = int(string)
    return dec

def get_pack_type(filed_type, field_size):
    if filed_type == "uint":
        return '<I'
    elif filed_type == "byte":
        return '<B'
    elif filed_type == "word":
        return '<H'
    elif filed_type == "array":
        return '<B'
    elif filed_type == "str":
        return str('<' + field_size + 's')
    else:
        print("[Error] - Unknown field type found {}".format(filed_type))
        sys.exit(1)

def pack_field(mi_section, fld, mi_config_file_name, output_bin):
    "Pack MI field based on its size and type"
    global Value_of_size_field
    with open(mi_config_file_name, newline='') as mi_config_csv:
        mi_config = csv.reader(mi_config_csv, delimiter=',')
        field_type = field_size = None
        for row in mi_config:
            if row[0] == fld:
                field_name = row[0]
                field_type = row[1]
                field_size = row[2]
        if field_size is None:
            print("[ERROR] - Field name {} not found in config file".format(fld))
            return None
        print("[INFO] - Packing Field: '{}'".format(field_name))

        if field_type in ('uint', 'byte', 'word'):
            filed_value = mi_section.get(fld)
            packed_value = pack(get_pack_type(field_type, field_size), str2dec(filed_value))
            output_bin.write(packed_value)
        elif field_type == 'str':
            filed_value = bytearray(mi_section.get(fld).encode('utf-8'))
            packed_value = pack(get_pack_type(field_type, field_size), filed_value)
            output_bin.write(packed_value)
        else:
            packed_value = writeAddrVal(mi_section.get(fld), output_bin)

        if field_name == "size":
            Value_of_size_field = str2dec(filed_value)

        return field_size

def pack_mi_data(mi_data, mi_config_file_name, output_bin):
    """Parse through MI data file, section by section, packing each field"""
    field_count = mi_size = 0
    for mi_section in mi_data.sections():
        for fld in mi_data[mi_section]:
            ret = pack_field(mi_data[mi_section], fld, mi_config_file_name, output_bin)
            if ret is None:
                return "Pack Failed!"
            else:
                mi_size += int(ret)
            field_count += 1
    print("[INFO] - MI data size = {}".format(mi_size))
    print("[INFO] - Field count = {}".format(field_count))
    return mi_size

def main(argv):
    parser = argparse.ArgumentParser(description="MCU MI binary file generator")
    parser.add_argument("-i", "--ini", required=True, help="MCU MI data file")
    parser.add_argument("-c", "--config", required=True, help="MI config file, specifying size and type")
    parser.add_argument("-v", '--version', action='version', version='%(prog)s - {}'.format(VERSION_STRING))
    args = parser.parse_args()

    if not os.path.isfile(args.ini):
        print("Error: ini file ({0}) not found!".format(os.path.realpath(args.ini)))
        sys.exit(1)

    if not os.path.isfile(args.config):
        print("Error: config file ({0}) not found!".format(os.path.realpath(args.config)))
        sys.exit(1)

    # Stage 1: Allow user to input dynamic MI fileds, write the data to modified MI data file.
    # Input: mi.ini
    # Output: mi_modified.ini
    # Stage 1: Allow user to input dynamic MI fields
    str_no_ext = os.path.splitext(args.ini)[0]
    modified_mi_fl_name = str_no_ext + "_modified.ini"

    if os.path.isfile(modified_mi_fl_name):
        os.remove(modified_mi_fl_name)

    mi_data = configparser.ConfigParser(allow_no_value=True)
    mi_data.add_section('warning')
    mi_data.set('warning', "; This is an autogenerated file. !DO NOT MODIFY!")
    mi_data.read(args.ini)

    ret = edit_mi_data(mi_data)
    if ret:
        print("[ERROR] - MI data file modification Failed! Error: {}".format(ret))
        sys.exit(1)

    with open(modified_mi_fl_name, 'w') as config_out:
        mi_data.write(config_out, space_around_delimiters=False)
    print("[INFO] - MI data file:{} modified successfully".format(modified_mi_fl_name))

    # Stage 2: Generate MI bin file from modified MI data file
    # Determine output filename dynamically from fazit_id_string
    temp_mi = configparser.ConfigParser(allow_no_value=True)
    temp_mi.read(modified_mi_fl_name)

    if OEM_CONTENT_DYNAMIC_1 not in temp_mi or len(temp_mi[OEM_CONTENT_DYNAMIC_1].keys()) == 0:
        print("[ERROR] - '{}' section missing or empty in modified ini file!".format(OEM_CONTENT_DYNAMIC_1))
        sys.exit(1)

    first_key = list(temp_mi[OEM_CONTENT_DYNAMIC_1].keys())[0]  # 'fazit_id_string'
    fazit_value = temp_mi[OEM_CONTENT_DYNAMIC_1][first_key]

    # --- NEW: Save to 'bin' folder in parent directory ---
    parent_folder = os.path.dirname(os.path.abspath(__file__))  # parent folder of the script

    # Create a folder with the current date (YYYYMMDD)
    date_folder = datetime.now().strftime("%Y%m%d")
    output_folder = os.path.join(parent_folder, date_folder)
    os.makedirs(output_folder, exist_ok=True)  # create folder if it doesn't exist

    # Construct output file path
    output_file = os.path.join(output_folder, f"{fazit_value}.bin")
    # -----------------------------------------------

    if os.path.isfile(output_file):
        os.remove(output_file)
    output_bin = open(output_file, "ab")

    mi_data = configparser.ConfigParser(allow_no_value=True)
    mi_data.read(modified_mi_fl_name)

    # Pack MI data
    mi_size = pack_mi_data(mi_data, args.config, output_bin)
    output_bin.close()

    output_size = os.path.getsize(output_file)
    if output_size != (Value_of_size_field - 4):
        print("[ERROR] - miscalculation size info ({0})!".format(output_size))
        print("[ERROR] - miscalculation size info ({0})!".format(Value_of_size_field))
        sys.exit(1)

    # Calculate CRC32 and append
    with open(output_file, "rb") as f:
        output_bin_crc32 = str2dec(hex(zlib.crc32(f.read()) & 0xffffffff))
    print("[INFO] - CRC calculated: {}".format(hex(output_bin_crc32)))

    with open(output_file, "ab") as f:
        f.write(pack('<I', output_bin_crc32))

    print("[INFO] - MI bin file generated: '{}'".format(os.path.realpath(output_file)))

if __name__ == "__main__":
    main(sys.argv[1:])
