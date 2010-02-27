import re
import struct

DEFAULT_GEARMAN_PORT = 4730

NULL_CHAR = "\x00"
MAGIC_RES_STRING = "%sRES" % NULL_CHAR
MAGIC_REQ_STRING = "%sREQ" % NULL_CHAR

COMMAND_HEADER_SIZE = 12

# Gearman commands 1-9
GEARMAN_COMMAND_CAN_DO = 1
GEARMAN_COMMAND_CANT_DO = 2
GEARMAN_COMMAND_RESET_ABILITIES = 3
GEARMAN_COMMAND_PRE_SLEEP = 4
GEARMAN_COMMAND_NOOP = 6
GEARMAN_COMMAND_SUBMIT_JOB = 7
GEARMAN_COMMAND_JOB_CREATED = 8
GEARMAN_COMMAND_GRAB_JOB = 9

# Gearman commands 10-19
GEARMAN_COMMAND_NO_JOB = 10
GEARMAN_COMMAND_JOB_ASSIGN = 11
GEARMAN_COMMAND_WORK_STATUS = 12
GEARMAN_COMMAND_WORK_COMPLETE = 13
GEARMAN_COMMAND_WORK_FAIL = 14
GEARMAN_COMMAND_GET_STATUS = 15
GEARMAN_COMMAND_ECHO_REQ = 16
GEARMAN_COMMAND_ECHO_RES = 17
GEARMAN_COMMAND_SUBMIT_JOB_BG = 18
GEARMAN_COMMAND_ERROR = 19

# Gearman commands 20-29
GEARMAN_COMMAND_STATUS_RES = 20
GEARMAN_COMMAND_SUBMIT_JOB_HIGH = 21
GEARMAN_COMMAND_SET_CLIENT_ID = 22
GEARMAN_COMMAND_CAN_DO_TIMEOUT = 23
GEARMAN_COMMAND_ALL_YOURS = 24
GEARMAN_COMMAND_WORK_EXCEPTION = 25
GEARMAN_COMMAND_OPTION_REQ = 26
GEARMAN_COMMAND_OPTION_RES = 27
GEARMAN_COMMAND_WORK_DATA = 28
GEARMAN_COMMAND_WORK_WARNING = 29

# Gearman commands 30-39
GEARMAN_COMMAND_GRAB_JOB_UNIQ = 30
GEARMAN_COMMAND_JOB_ASSIGN_UNIQ = 31
GEARMAN_COMMAND_SUBMIT_JOB_HIGH_BG = 32
GEARMAN_COMMAND_SUBMIT_JOB_LOW = 33
GEARMAN_COMMAND_SUBMIT_JOB_LOW_BG = 34

COMMAND_PARAMS = {
    # Gearman commands 1-9
    GEARMAN_COMMAND_CAN_DO: ["func"],
    GEARMAN_COMMAND_CANT_DO: ["func"],
    GEARMAN_COMMAND_RESET_ABILITIES: [],
    GEARMAN_COMMAND_PRE_SLEEP: [],
    GEARMAN_COMMAND_NOOP: [],
    GEARMAN_COMMAND_SUBMIT_JOB: ["func", "unique", "data"],
    GEARMAN_COMMAND_JOB_CREATED: ["handle"],
    GEARMAN_COMMAND_GRAB_JOB: [],

    # Gearman commands 10-19
    GEARMAN_COMMAND_NO_JOB: [],
    GEARMAN_COMMAND_JOB_ASSIGN: ["handle", "func", "data"],
    GEARMAN_COMMAND_WORK_STATUS: ["handle", "numerator", "denominator"],
    GEARMAN_COMMAND_WORK_COMPLETE: ["handle", "data"],
    GEARMAN_COMMAND_WORK_FAIL: ["handle"],
    GEARMAN_COMMAND_GET_STATUS: ["handle"],
    GEARMAN_COMMAND_ECHO_REQ: ["text"],
    GEARMAN_COMMAND_ECHO_RES: ["text"],
    GEARMAN_COMMAND_SUBMIT_JOB_BG: ["func", "unique", "data"],
    GEARMAN_COMMAND_ERROR: ["err_code", "err_text"],

    # Gearman commands 20-29
    GEARMAN_COMMAND_STATUS_RES: ["handle", "known", "running", "numerator", "denominator"],
    GEARMAN_COMMAND_SUBMIT_JOB_HIGH: ["func", "unique", "data"],
    GEARMAN_COMMAND_SET_CLIENT_ID: ["client_id"],
    GEARMAN_COMMAND_CAN_DO_TIMEOUT: ["func", "timeout"],
    GEARMAN_COMMAND_ALL_YOURS: [],
    GEARMAN_COMMAND_WORK_EXCEPTION: ["handle", "data"],
    GEARMAN_COMMAND_OPTION_REQ: ["option_name"],
    GEARMAN_COMMAND_OPTION_RES: ["option_name"],
    GEARMAN_COMMAND_WORK_DATA: ["handle", "data"],
    GEARMAN_COMMAND_WORK_WARNING: ["handle", "data"],

    # Gearman commands 30-39
	GEARMAN_COMMAND_GRAB_JOB_UNIQ: [],
	GEARMAN_COMMAND_JOB_ASSIGN_UNIQ: ["handle", "func", "unique", "data"],
	GEARMAN_COMMAND_SUBMIT_JOB_HIGH_BG: ["func", "unique", "data"],
	GEARMAN_COMMAND_SUBMIT_JOB_LOW: ["func", "unique", "data"],
	GEARMAN_COMMAND_SUBMIT_JOB_LOW_BG: ["func", "unique", "data"],

}

GEARMAN_SERVER_COMMAND_STATUS = "status"
GEARMAN_SERVER_COMMAND_VERSION = "version"
GEARMAN_SERVER_COMMAND_WORKERS = "workers"
GEARMAN_SERVER_COMMAND_MAXQUEUE = "maxqueue"
GEARMAN_SERVER_COMMAND_SHUTDOWN = "shutdown"

txt_command_re = re.compile("^[\w\n\r]+")

class ProtocolError(Exception):
    pass

def parse_command(databuffer, is_response=True):
    """Parse data and return (function name, argument dict, command size)
    or (None, None, data) if there's not enough data for a complete command.
    """
    databuffer_size = len(databuffer)
    magic = None
    cmd_type = None
    cmd_args = None
    cmd_len = 0
    expected_packet_size = None
    
    if databuffer_size == 0:
        return cmd_type, cmd_args, cmd_len

    if is_response:
        expected_magic = MAGIC_RES_STRING
    else:
        expected_magic = MAGIC_REQ_STRING

    if COMMAND_HEADER_SIZE <= databuffer_size:
        # By default, we'll assume we're dealing with a gearman command
        magic, cmd_type, cmd_len = struct.unpack("!4sLL", databuffer[:COMMAND_HEADER_SIZE])
        expected_packet_size = COMMAND_HEADER_SIZE + cmd_len

    if magic != expected_magic:
        if not txt_command_re.match(databuffer):
            raise ProtocolError("Malformed Magic")

        # If we think this is a potential server command, parse it out
        if '\n' in databuffer:
            raw_server_command, databuffer = databuffer.split('\n', 1)
            return raw_server_command.strip(), databuffer, len(raw_server_command) + 1
        else:
            return None, None, 0

    if databuffer_size < expected_packet_size:
        return None, None, 0

    cmd_params = COMMAND_PARAMS.get(cmd_type, None)
    if cmd_params is None:
        raise ProtocolError("Unknown message received: %d" % cmd_type)

    number_of_params = len(cmd_params)
    split_arguments = []
    if number_of_params > 0:
        post_header_data = databuffer[COMMAND_HEADER_SIZE:expected_packet_size]
        split_arguments = post_header_data.split(NULL_CHAR, number_of_params - 1)

    if len(split_arguments) != number_of_params:
        raise ProtocolError("Received wrong number of arguments to %s" % cmd_type)

    # Iterate through the split arguments and assign them labels based on their order
    cmd_args = dict(zip(cmd_params, split_arguments))
    return cmd_type, cmd_args, expected_packet_size

def pack_command(cmd_type, cmd_args, is_response=False):
    expected_cmd_params = COMMAND_PARAMS.get(cmd_type, None)
    if expected_cmd_params is None:
        raise ProtocolError("Unknown message received: %s" % cmd_type)

    assert set(expected_cmd_params) == set(cmd_args.keys()), "Command arguments not equal to expected: %r != %r" % (set(expected_cmd_params), set(cmd_args.keys()))

    data_items = []
    for param in expected_cmd_params:
        raw_value = cmd_args[param]
        raw_value = raw_value or ""

        data_items.append(str(raw_value))

    raw_binary_data = NULL_CHAR.join(data_items)
    if is_response:
        magic = MAGIC_RES_STRING
    else:
        magic = MAGIC_REQ_STRING

    return "%s%s" % (struct.pack("!4sII", magic, cmd_type, len(raw_binary_data)), raw_binary_data)
