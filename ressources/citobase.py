"""Basic functionalities to communicate over Cito protocol."""

import socket
from struct import pack, unpack
from time import time

import serial
import serial.serialutil


class CitoBase:
    """Basic functionalities to communicate over Cito protocol."""

    (ETHERNET, SERIAL) = (0, 1)
    ethernet_timeout = 1.0  # Ethernet timeout in seconds
    serial_timeout = 1000  # serial timeout in milliseconds

    # Constants for parameters and values
    PNUM_COMMAND = 1001  # Command

    PNUM_POWER_SETPOINT = 1206  # Power set point

    PNUM_STATE = 8000  # Generator status
    PNUM_RF_FREQUENCY = 8011  # Generator frequency
    PNUM_FORW_POWER = 8021  # Forward power monitor
    PNUM_REFL_POWER = 8022  # Reflected power monitor
    PNUM_LOAD_POWER = 8023  # Load power monitor
    PNUM_CEX_FREQUENCY = 8041  # CEX frequency

    PVAL_CMD_RFOFF = 0  # RF on
    PVAL_CMD_RFON = 1  # RF off
    PVAL_CMD_RESET = 9  # Reset
    PVAL_STATE_INIT = 0  # Init
    PVAL_STATE_RF_OFF = 1  # RF off
    PVAL_STATE_RF_ON = 2  # RF on
    PVAL_STATE_ERROR = 3  # Error
    PVAL_STATE_CALIB = 4  # Calibration
    PVAL_STATE_UPDATE = 5  # Update
    PVAL_STATE_BLOCKED = 6  # Blocked

    # TODO: Exception codes do not match responses from cito. ECR0100 created.
    # At the moment generator returns exception code with highest bit set. See
    # modbus table below.
    shft_exception_codes = {
        0x00: "No errors",
        0x01: "Unknown parameter or illegal function code",
        0x04: "Value invalid",
        0x05: "Parameter not writeable",
        0x06: "Parameter not readable",
        0x07: "Stop",
        0x08: "Not allowed",
        0x09: "Wrong data type",
        0x0A: "Internal error",
        0x0B: "Value too high",
        0x0C: "Value too low"}

    modbus_exception_codes = {
        0x00: "NO_ERRORS",
        0x01: "EXCEPT_ILLEGAL_FUNCTION",
        0x02: "EXCEPT_ILLEGAL_DATA_ADDRESS",
        0x03: "EXCEPT_ILLEGAL_DATA_VALUE",
        0x04: "EXCEPT_SLAVE_DEVICE_FAILURE",
        0x05: "EXCEPT_ACKNOWLEDGE",
        0x06: "EXCEPT_SLAVE_DEVICE_BUSY",
        0x07: "EXCEPT_NEGATIVE_ACKNOWLEDGE",
        0x08: "EXCEPT_MEMORY_PARITY_ERROR",
        0x0A: "EXCEPT_GATEWAY_PATH_UNAVAILABLE",
        0x0B: "EXCEPT_GATEWAY_TARGET_DEVICE_FAILED_TO_RESPOND",
        0x81: "SHFT_PARAFAULT_UNKNOWN_PARAMETER",
        0x82: "SHFT_PARAFAULT_INDEX",
        0x83: "SHFT_PARAFAULT_INDEX_MAX",
        0x84: "SHFT_PARAFAULT_VALUE_INVALID",
        0x85: "SHFT_PARAFAULT_NOT_WRITEABLE",
        0x86: "SHFT_PARAFAULT_NOT_READABLE",
        0x87: "SHFT_PARAFAULT_STOP",
        0x88: "SHFT_PARAFAULT_NOT_ALLOWED",
        0x89: "SHFT_PARAFAULT_TYPE",
        0x8A: "SHFT_PARAFAULT_INTERNAL",
        0x8B: "SHFT_PARAFAULT_VALUE_OVL",
        0x8C: "SHFT_PARAFAULT_VALUE_NOVL",
        0xC1: "ISOCKET_INVALID_ARGUMENT",
        0xC2: "ISOCKET_READ_ERROR",
        0xC3: "ISOCKET_WRITE_ERROR",
        0xC4: "ISOCKET_WRITE_TIMEOUT",
        0xC5: "ISOCKET_READ_TIMEOUT",
        0xC6: "ISOCKET_INVALID_REPLY",
        0xD1: "RFGENTHR_PARAMETER_INVALID",
        0xD2: "RFGENTHR_PARAMETER_INVALID_CASE_READ",
        0xD3: "RFGENTHR_PARAMETER_INVALID_CASE_WRITE",
        0xD4: "RFGENTHR_PARAMETER_TOO_MANY_PARAINFOS",
        0xD5: "RFGENTHR_PARAMETER_STOP_REQUESTED",
        0xD6: "RFGENTHR_PARAMETER_CANCELED",
        0xD7: "RFGENTHR_TIMEOUT",
        0xE1: "DLL_NO_FREE_HANDLE",
        0xE2: "DLL_CREATE_CONNECTION_FAILED",
        0xE3: "DLL_INVALID_HANDLE",
        0xE4: "DLL_INVALID_PARAMETER"}

    ##########################################################################
    # Initialization
    ##########################################################################
    def __init__(self, host_addr, host_port=None, host_mode=None,
                 host_baudrate=None, host_bytesize=None, host_parity=None,
                 host_stopbits=None):
        """
        Connect to Cito-Protocol-enabled device.

        :param host_addr: cito host address (IP address, host name or COM port)
        :param host_port: Port for Ethernet communication
        :param host_mode: 0: Ethernet, 1: Serial communication
        """
        self.host_addr = host_addr

        # Default host port for Modbus/TCP is 502
        if host_port is None:
            self.host_port = 502
        else:
            if (host_port > 0 and host_port <= 65535):
                self.host_port = host_port
            else:
                raise ValueError(
                    'Invalid communication port ({0})'.format(host_port))

        # Try to guess communication mode (serial or Ethernet) from host_address
        # if no mode has been specified
        if host_mode is None:
            # Host addresses not starting with "COM..." are handled as Ethernet
            # addresses
            if not (self.host_addr[0:3].upper() == "COM"):
                self.host_mode = self.ETHERNET
            # Check if COM port number is in range
            else:
                try:
                    # COM port number must be in the range of 1 to 255
                    com_port_number = int(self.host_addr[3:])
                    if (com_port_number > 0) and (com_port_number <= 255):
                        self.host_mode = self.SERIAL
                # Otherwise it is an Ethernet connection
                except ValueError:
                    self.host_mode = self.ETHERNET

        # Host communication mode (serial or Ethernet) has explicitly been
        # specified
        else:
            if host_mode == self.ETHERNET:
                self.host_mode = self.ETHERNET
            elif host_mode == self.SERIAL:
                self.host_mode = self.SERIAL
            else:
                raise ValueError(
                    'Unknown communication mode ({0}).'.format(host_mode))

        # Parameters for serial communication
        if host_baudrate is None:
            self.baudrate = 115200
        else:
            self.baudrate = host_baudrate

        if host_bytesize is None:
            self.bytesize = serial.EIGHTBITS
        else:
            self.bytesize = host_bytesize

        if host_parity is None:
            self.parity = serial.PARITY_EVEN
        else:
            self.parity = host_parity

        if host_stopbits is None:
            self.stopbits = serial.STOPBITS_ONE
        else:
            self.stopbits = host_stopbits

        # Set first transaction number to start with
        self.transaction_number = 0x0000

    ##########################################################################
    # Connection Handling
    ##########################################################################

    def open(self):
        """
        Open communication channel to cito generator.

        :return: True if successful, False in case of error
        """
        # Create a TCP/IP socket
        if self.host_mode == self.ETHERNET:
            try:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.settimeout(self.ethernet_timeout)
                self._socket.connect((self.host_addr, self.host_port))
            except socket.timeout:
                return False
            except Exception:
                return False
            return True

        # Create serial socket
        elif self.host_mode == self.SERIAL:
            self._socket = serial.Serial()
            try:
                self._socket.setPort(self.host_addr)
                self._socket.baudrate = self.baudrate
                self._socket.bytesize = self.bytesize
                self._socket.parity = self.parity
                self._socket.stopbits = self.stopbits
                self._socket.open()
            except serial.serialutil.SerialException:
                return False
            except Exception:
                return False
            return True

        # Unknown host mode. This case should not occur.
        else:
            raise ValueError(
                'Unknown communication mode ({0}).'.format(
                    self.host_mode))

    def isopen(self):
        """
        Return status of communication channel to cito generator.

        :return: Returns boolean value. True if channel is open, false if
        channel is closed or not initialized
        """
        state = False

        if self.host_mode == self.ETHERNET:
            try:
                if self._socket is not None:
                    return True
            except BaseException:
                pass
            return False

        elif self.host_mode == self.SERIAL:
            try:
                state = self._socket.is_open
            except Exception:
                state = False

        return state

    def close(self):
        """Terminates communication with cito generator."""
        if self.host_mode == self.ETHERNET:
            self._socket.shutdown(2)
            self._socket.close()

        elif self.host_mode == self.SERIAL:
            self._socket.close()

    ##########################################################################
    # Exchange data with cito
    ##########################################################################

    def _data_exchange(self, tx_data=None):
        if tx_data is None:
            tx_data = []

        tx_array = []  # Buffer for outbound data
        rx_data_buffer = []  # Buffer for unformatted received data
        # Buffer for complete received data including overhead (Ethernet, CRC16,
        # etc.)
        rx_data_recv = []
        rx_data_shft = []  # Buffer for SHFT protocol part of received data
        ser_rx_complete = False  # Flag for completion of serial reception
        tx_function_code = 0x00  # Function code of last transaction
        rx_exception_code = 0x00  # Exception code for last transaction

        # Assemble data packet to send for Ethernet communication
        if self.host_mode == self.ETHERNET:
            # Get next transaction number
            tx_transaction_number = self.transaction_number
            self.transaction_number += 1
            if self.transaction_number > 0xFFFF:
                self.transaction_number = 0x0000

            # Bytes 0 and 1 consist of transaction number
            tx_array.append((tx_transaction_number >> 8) & 0xFF)
            tx_array.append(tx_transaction_number & 0xFF)

            # Bytes 2 and 3 are always 0x00 by Modbus/TCP definition
            tx_array.append(0x00)
            tx_array.append(0x00)

            # Bytes 4 and 5 contain number of trailing bytes (the SHFT protocol
            # part)
            tx_data_array_len = len(tx_data)
            # Data must not be shorter than 4 or longer than 253 bytes
            if tx_data_array_len <= 4:
                raise ValueError(
                    f'Data packet too short ({tx_data_array_len} bytes)')
            if tx_data_array_len >= 253:
                raise ValueError(
                    f'Data packet too long ({tx_data_array_len} bytes)')
            tx_array.append((tx_data_array_len >> 8) & 0xFF)
            tx_array.append(tx_data_array_len & 0xFF)

            # Bytes 5 to n contain the SHFT protocol part (data submitted in
            # function call)
            for tx_data_array_byte in tx_data:
                tx_array.append(tx_data_array_byte)

            # Extract transmit function code (FC)
            if len(tx_array) >= 8:
                tx_function_code = tx_array[7]

        # Construct data packet to send for serial communication
        elif (self.host_mode == self.SERIAL):
            # Bytes 1 to n contain the SHFT protocol part (data submitted in
            # function call)
            for tx_data_array_byte in tx_data:
                tx_array.append(tx_data_array_byte)

            # Bytes n+1 and n+2 contain the CRC16 checksum
            tx_array.extend(self._calc_crc16(tx_array))

            # Extract transmit function code (FC)
            if len(tx_array) >= 2:
                tx_function_code = tx_array[1]

        # Try to send data to host
        if self.host_mode == self.ETHERNET:
            try:
                self._socket.send(bytearray(tx_array))
            except socket.timeout:
                return (0xC4, rx_data_buffer)  # Socket write timeout
            except Exception:
                return (0xC3, rx_data_buffer)  # Socket write error

        elif self.host_mode == self.SERIAL:
            try:
                self._socket.write(tx_array)
            except socket.timeout:
                return (0xC4, rx_data_buffer)  # Socket write timeout
            except Exception:
                return (0xC3, rx_data_buffer)  # Socket write error

        # Try to read data from host via Ethernet
        if self.host_mode == self.ETHERNET:
            try:
                rx_data_buffer = self._socket.recv(300)
            except socket.timeout:
                return (0xC5, rx_data_buffer)  # Socket read timeout
            except Exception:
                return (0xC2, rx_data_buffer)  # Socket read error

            # Different handling of response for Python 2.7 and 3.x. See:
            # https://stackoverflow.com/questions/39103164/ord-function-in-python2-7-and-python-3-4-are-different
            for rx_buffer_value in rx_data_buffer:
                if (isinstance(rx_buffer_value, int)):
                    rx_data_recv.append(rx_buffer_value)
                else:
                    rx_data_recv.append(ord(rx_buffer_value[0]))

        # Try to read data from host via RS-232
        elif self.host_mode == self.SERIAL:
            rx_start_time = round(1000 * time())    # Start time in milliseconds
            while not ser_rx_complete:
                try:
                    while (self._socket.in_waiting):
                        rx_data_buffer.append(ord(self._socket.read()))
                except serial.SerialException:
                    return (0xC2, rx_data_buffer)  # Socket read error

                # Validate checksum of received data packet
                if len(rx_data_buffer) >= 5:
                    rx_crc16 = rx_data_buffer[-2:]
                    calc_crc16 = self._calc_crc16(rx_data_buffer[:-2])
                    # Transaction is only complete when correct CRC16 has been
                    # received
                    if (rx_crc16 == list(calc_crc16)):
                        ser_rx_complete = True

                # Check for timeout
                rx_timeout = round(1000 * time()) - rx_start_time
                if rx_timeout > self.serial_timeout:
                    return (0xC5, rx_data_buffer)  # Socket read timeout

            rx_data_recv = rx_data_buffer[:]

        # Remove leading Ethernet (Modbus/TCP) transport protocol
        if (self.host_mode == self.ETHERNET):
            rx_array_len = len(rx_data_recv)
            if rx_array_len >= 9:
                rx_modbus_length_field = (
                    rx_data_recv[4] * 256) + rx_data_recv[5]
                # Check if number of received bytes matches the length declared
                # in length fields
                if (rx_array_len == (rx_modbus_length_field + 6)):
                    # Remove six trailing bytes with transaction number,
                    # protocol identifier, and modbus length info
                    rx_data_shft = rx_data_recv[6:]

        else:
            # For serial communication remove two trailing bytes containing
            # CRC16 checksum
            rx_data_shft = rx_data_recv[:-2]

        rx_function_code = rx_data_shft[1]

        # Read command (0x41)
        if rx_function_code == 0x41:
            # Is there anything to do here? Probably nothing to check at a read
            # command...
            pass

        # Write command (0x42): Transaction is successful when sent and received
        # data are identical
        elif rx_function_code == 0x42:
            # If sent and received data differ, a transmission error occurred
            if rx_data_recv != tx_array:
                rx_exception_code = 0xC6

        # Check if exception function code has been received
        elif rx_function_code == (tx_function_code + 0x80):
            rx_exception_code = rx_data_shft[2]

        # Catchall function, should never occur
        else:
            rx_exception_code = 0xFF

        return (rx_exception_code, rx_data_shft)

    def decode_cito_exception_code(self, exception_code):
        """
        Decode exception code, returns clear text error message.

        :param exception_code: Exception code (0x00 - 0xFF)
        :return: String with clear text error message
        """
        if exception_code in self.modbus_exception_codes:
            return self.modbus_exception_codes[exception_code]
        else:
            return "UNKNOWN_EXCEPTION_CODE"

    ##########################################################################
    # Reading Parameters
    ##########################################################################

    def read_integer(self, parameter: int):
        """
        Read integer value from cito generator.

        :param parameter: Parameter number
        :return: List containing exception code and integer value
        """
        tx_array = [0x0A, 0x41, 0x00, 0x00, 0x00, 0x01]
        tx_array[2] = (parameter >> 8) & 0xFF
        tx_array[3] = parameter & 0xFF

        # Forward transmit data to data transfer function
        rx_exception_code, rx_data = self._data_exchange(tx_array)
        rx_data_int = 0

        # Transfer was successful when Exception Code is 0x00 --> Decode
        # response.
        if (rx_exception_code == 0x00) and (len(rx_data) == 7):
            rx_data_value = rx_data[3:]
            rx_data_int = unpack('!i', bytes(bytearray(rx_data_value)))[0]

        return (rx_exception_code, rx_data_int)

    def read_float(self, parameter: int):
        """
        Read float value from cito generator.

        :param parameter: Parameter number
        :return: List containing exception code and float value
        """
        tx_array = [0x0A, 0x41, 0x00, 0x00, 0x00, 0x01]
        tx_array[2] = (parameter >> 8) & 0xFF
        tx_array[3] = parameter & 0xFF

        # Forward transmit data to data transfer function
        rx_exception_code, rx_data = self._data_exchange(tx_array)
        rx_data_float = 0

        # Transfer was successful when Exception Code is 0x00 --> Decode
        # response.
        if (rx_exception_code == 0x00) and (len(rx_data) == 7):
            rx_data_value = rx_data[3:]
            rx_data_float = round(
                unpack(
                    '!f',
                    bytes(
                        bytearray(rx_data_value)))[0],
                6)

        return (rx_exception_code, rx_data_float)

    def read_string(self, parameter: int):
        """
        Read string from cito generator.

        :param parameter: Parameter number
        :return: List containing exception code and string
        """
        tx_array = [0x0A, 0x41, 0x00, 0x00, 0x00, 0x01]
        tx_array[2] = (parameter >> 8) & 0xFF
        tx_array[3] = parameter & 0xFF

        # Forward transmit data to data transfer function
        rx_exception_code, rx_data = self._data_exchange(tx_array)
        rx_data_string = ""

        # Transfer was successful when Exception Code is 0x00 --> Decode
        # response.
        if rx_exception_code == 0x00:
            rx_modbus_length_field = rx_data[2]
            for data_byte_number in range(rx_modbus_length_field):
                rx_data_string += chr(rx_data[3 + data_byte_number])

        return (rx_exception_code, rx_data_string)

    def read_ip_addr(self, parameter: int):
        """
        Read integer value from cito generator.

        :param parameter: Parameter number
        :return: List containing exception code and decoded IP address as
        string, e.g. "169.254.1.1"
        """
        tx_array = [0x0A, 0x41, 0x00, 0x00, 0x00, 0x01]
        tx_array[2] = (parameter >> 8) & 0xFF
        tx_array[3] = parameter & 0xFF

        # Forward transmit data to data transfer function
        rx_exception_code, rx_data = self._data_exchange(tx_array)
        rx_data_int = 0

        # Transfer was successful when Exception Code is 0x00 --> Decode
        # response.
        if (rx_exception_code == 0x00) and (len(rx_data) == 7):
            rx_data_value = rx_data[3:]
            rx_data_int = unpack('!I', bytes(bytearray(rx_data_value)))[0]

        rx_data_ip = ""
        if rx_exception_code == 0:
            ip_byte_1 = (rx_data_int >> 24)
            ip_byte_2 = (rx_data_int >> 16) % 256
            ip_byte_3 = (rx_data_int >> 8) % 256
            ip_byte_4 = rx_data_int % 256
            rx_data_ip = "{0}.{1}.{2}.{3}".format(
                ip_byte_1, ip_byte_2, ip_byte_3, ip_byte_4)

        return (rx_exception_code, rx_data_ip)

    ##########################################################################
    # Writing Parameters
    ##########################################################################

    def write_integer(self, parameter: int, value: int):
        """
        Write integer value to cito generator.

        :param parameter: Parameter number
        :param value: Integer value
        :return: Exception code
        """
        tx_array = [0x0A, 0x42, 0x00, 0x00]
        tx_array[2] = (parameter >> 8) & 0xFF
        tx_array[3] = parameter & 0xFF
        value_pack = pack("!i", value)
        for value_pack_byte in value_pack:
            # Pack function creates int in Python 2.7 and chr in Python 3.5
            if isinstance(value_pack_byte, int):
                tx_array.append(value_pack_byte)
            else:
                tx_array.append(ord(value_pack_byte))

        # Forward transmit data to data transfer function
        rx_exception_code, rx_data = self._data_exchange(tx_array)
        return rx_exception_code

    def write_float(self, parameter: int, value: float):
        """
        Write float value to cito generator.

        :param parameter: Parameter number
        :param value: Float value
        :return: Exception code
        """
        tx_array = [0x0A, 0x42, 0x00, 0x00]
        tx_array[2] = (parameter >> 8) & 0xFF
        tx_array[3] = parameter & 0xFF
        value_pack = pack("!f", round(value, 6))
        for value_pack_byte in value_pack:
            # Pack function creates int in Python 2.7 and chr in Python 3.5
            if isinstance(value_pack_byte, int):
                tx_array.append(value_pack_byte)
            else:
                tx_array.append(ord(value_pack_byte))

        # Forward transmit data to data transfer function
        rx_exception_code, rx_data = self._data_exchange(tx_array)

        return rx_exception_code

    def write_string(self, parameter: int, value: str):
        """
        Write string to cito generator.

        :param parameter: Parameter number
        :param value: String
        :return: Exception code
        """
        tx_array = [0x0A, 0x42, 0x00, 0x00]
        tx_array[2] = (parameter >> 8) & 0xFF
        tx_array[3] = parameter & 0xFF
        for value_byte in value:
            tx_array.append(ord(value_byte))
        tx_array.append(0x00)

        # Forward transmit data to data transfer function
        rx_exception_code, rx_data = self._data_exchange(tx_array)

        return rx_exception_code

    def write_ip_addr(self, parameter: int, value: str):
        """
        Write IP address to cito generator.

        :param parameter: Parameter number
        :param value: String containing IP address, e.g. "169.254.1.1"
        :return: Exception code
        """
        # An IP address must consist of four bytes separated by dots
        ip_array = value.split('.')
        if len(ip_array) != 4:
            return 0x04

        # Values of an IP address must be integer
        try:
            ip_byte_1 = int(ip_array[0])
            ip_byte_2 = int(ip_array[1])
            ip_byte_3 = int(ip_array[2])
            ip_byte_4 = int(ip_array[3])
        except Exception:
            return 0x04

        # Values of an IP address must be between 0 and 255
        if not (0 <= ip_byte_1 <= 255 and 0 <= ip_byte_2 <= 255 and  # noqa W504
                0 <= ip_byte_3 <= 255 and 0 <= ip_byte_4 <= 255):
            return 0x04

        # Calculate integer value from four bytes
        ip_value_int = (ip_byte_1 * (256 ** 3) + ip_byte_2 * (256 ** 2) +  # noqa W504
                        ip_byte_3 * 256 + ip_byte_4)

        tx_array = [0x0A, 0x42, 0x00, 0x00]
        tx_array[2] = (parameter >> 8) & 0xFF
        tx_array[3] = parameter & 0xFF

        # Pack and send integer value
        value_pack = pack("!I", ip_value_int)
        for value_pack_byte in value_pack:
            # Pack function creates int in Python 2.7 and chr in Python 3.5
            if isinstance(value_pack_byte, int):
                tx_array.append(value_pack_byte)
            else:
                tx_array.append(ord(value_pack_byte))

        # Forward transmit data to data transfer function
        rx_exception_code, rx_data = self._data_exchange(tx_array)

        return rx_exception_code

    ##########################################################################
    # Error / Warning handling
    ##########################################################################

    def read_errors_as_text(self):
        """
        Read error messages and states from cito generator.

        :return: Array containing error texts and state
        """
        error_array = []
        # Error message texts are stored in parameter 8101 through 8131 (odd
        # numbers only)
        for error_counter in range(8101, 8133, 2):
            error_text = self.read_string(error_counter)
            # Reading was successful and parameter is not empty
            if (error_text[0] == 0) and (len(error_text[1]) > 0):
                # Get error state that is stored in parameter succeeding error
                # parameter
                error_state = self.read_integer(error_counter + 1)
                error_array.append([error_text[1], error_state[1]])
        return error_array

    def read_errors_as_numbers(self):
        """
        Read error messages and states from cito generator.

        :return: Array containing error numbers and state
        """
        error_array = []
        # Error message numbers are stored in parameter 8133 through 8148
        for error_offset in range(0, 17):
            error_number = self.read_integer(8133 + error_offset)
            # Reading was successful and parameter is not empty
            if (error_number[0] == 0) and (error_number[1] > 0):
                # Get error state
                error_state = self.read_integer(8102 + (2 * error_offset))
                error_array.append([error_number[1], error_state[1]])
        return error_array

    def read_warnings_as_text(self):
        """
        Read warning messages from cito generator.

        :return: Array containing warning texts
        """
        warn_array = []
        # Warning message texts are stored in parameter 8151 through 8166
        for warn_counter in range(8151, 8167):
            warn_text = self.read_string(warn_counter)
            # Reading was successful and parameter is not empty
            if (warn_text[0] == 0) and (len(warn_text[1]) > 0):
                warn_array.append(warn_text[1])
        return warn_array

    def read_warnings_as_numbers(self):
        """
        Read warning messages from cito generator.

        :return: Array containing warning numbers
        """
        warn_array = []
        # Warning message numbers are stored in parameter 8167 through 8182
        for warn_counter in range(8167, 8183):
            warn_number = self.read_integer(warn_counter)
            # Reading was successful and parameter is not empty
            if (warn_number[0] == 0) and (warn_number[1] > 0):
                warn_array.append(warn_number[1])
        return warn_array

    ##########################################################################
    # High level functions for commonly used features / calls
    ##########################################################################

    def set_rf_on(self, rf_on=True):
        """
        Turn power output of generator on.

        :param rf_on: Optional boolean parameter set to True by default. When
        set to False, RF will be turned on
        :return: Exception code
        """
        if rf_on:
            exception_code = self.write_integer(
                self.PNUM_COMMAND, self.PVAL_CMD_RFON)
        else:
            exception_code = self.write_integer(
                self.PNUM_COMMAND, self.PVAL_CMD_RFOFF)
        return exception_code

    def set_rf_off(self, rf_off=True):
        """
        Turn power output of generator off.

        :param rf_off: Optional boolean parameter set to True by default. When
        set to False, RF will be turned off
        :return: Exception code
        """
        if rf_off:
            exception_code = self.write_integer(
                self.PNUM_COMMAND, self.PVAL_CMD_RFOFF)
        else:
            exception_code = self.write_integer(
                self.PNUM_COMMAND, self.PVAL_CMD_RFON)
        return exception_code

    def reset_errors(self):
        """
        Reset all errors with status 'revoked'.

        Command cannot clear errors with status 'enduring' or 'persistent'.
        :return: Exception code
        """
        return self.write_integer(self.PNUM_COMMAND, self.PVAL_CMD_RESET)

    def set_power_setpoint_watts(self, value: int):
        """
        Set power setpoint of generator.

        :param value: Power in watts.
        :return: Exception code
        """
        if not isinstance(value, int):
            return 0x04
        else:
            exception_code = self.write_integer(
                self.PNUM_POWER_SETPOINT, 1000 * value)
        return exception_code

    def get_power_setpoint_watts(self):
        """
        Get power setpoint of generator.

        :return: List containing exception code and integer value with power
        setpoint in watts
        """
        exception_code, value = self.read_integer(self.PNUM_POWER_SETPOINT)
        return exception_code, int(value / 1000)

    def get_rf_frequency(self):
        """
        Read current RF frequency from generator.

        :return: List containing exception code and integer value with RF
        frequency in kHz
        """
        exception_code, value = self.read_integer(self.PNUM_RF_FREQUENCY)
        return exception_code, int(value / 1000)

    def get_cex_frequency(self):
        """
        Read current CEX frequency from generator.

        :return: List containing exception code and integer value with CEX
        frequency in kHz
        """
        exception_code, value = self.read_integer(self.PNUM_CEX_FREQUENCY)
        return exception_code, int(value / 1000)

    def get_forward_power_watts(self):
        """
        Read current forward power from generator.

        :return: List containing exception code and integer value with
        forward power in watts
        """
        exception_code, value = self.read_integer(self.PNUM_FORW_POWER)
        return exception_code, int(value / 1000)

    def get_reflected_power_watts(self):
        """
        Read current reflected power from generator.

        :return: List containing exception code and integer value with reflected
        power in watts
        """
        exception_code, value = self.read_integer(self.PNUM_REFL_POWER)
        return exception_code, int(value / 1000)

    def get_load_power_watts(self):
        """
        Read current load power from generator.

        :return: List containing exception code and integer value with load
        power in watts
        """
        exception_code, value = self.read_integer(self.PNUM_LOAD_POWER)
        return exception_code, int(value / 1000)

    def get_rf_status_int(self):
        """
        Read current status of generator.

        :return: List containing exception code and status of generator as
        integer value
        """
        exception_code, value = self.read_integer(self.PNUM_STATE)
        return exception_code, value

    def get_rf_status_string(self):
        """
        Read current status of generator.

        :return: List containing exception code and string containing status of
        generator
        """
        exception_code, value = self.read_integer(self.PNUM_STATE)
        if value == self.PVAL_STATE_INIT:
            status = "Init"
        elif value == self.PVAL_STATE_RF_OFF:
            status = "RF off"
        elif value == self.PVAL_STATE_RF_ON:
            status = "RF on"
        elif value == self.PVAL_STATE_ERROR:
            status = "Error"
        elif value == self.PVAL_STATE_CALIB:
            status = "Calibration"
        elif value == self.PVAL_STATE_UPDATE:
            status = "Update"
        elif value == self.PVAL_STATE_BLOCKED:
            status = "Blocked"
        else:
            status = "Undefined"
        return exception_code, status

    def _calc_crc16(self, data):
        """
        Calculate CRC16 check sum for RS-232 data packet.

        :param data: Array containing data to be sent
        :return: List with two bytes CRC, MSB first
        """
        crc16_tab = [
            0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241,
            0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481, 0x0440,
            0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40,
            0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841,
            0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81, 0x1A40,
            0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
            0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641,
            0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081, 0x1040,
            0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
            0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441,
            0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80, 0xFE41,
            0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840,
            0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41,
            0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81, 0x2C40,
            0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
            0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041,
            0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281, 0x6240,
            0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441,
            0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41,
            0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881, 0x6840,
            0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
            0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40,
            0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681, 0x7640,
            0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
            0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241,
            0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481, 0x5440,
            0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
            0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841,
            0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81, 0x4A40,
            0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
            0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641,
            0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081, 0x4040]

        crc = 0
        for offset in range(0, len(data)):
            crc = (crc >> 8) ^ crc16_tab[(crc & 0xFF) ^ data[offset]]
        return (crc & 0xFF), ((crc & 0xFF00) >> 8)

    def _array_to_hex_string(self, array):
        hex_string = ""
        for value in array:
            hex_string += ("0x%02X " % value)
        return hex_string.rstrip()


if __name__ == '__main__':  # running sample
    cito_address = "COM5"  # ip: "10.6.0.59"
    citoctrl = CitoBase(cito_address)
    if citoctrl.open():
        print("Label:   {0}".format(citoctrl.read_string(10)[1]))
        citoctrl.write_ip_addr("169.254.1.1")
        print("IP Addr: {0}".format(citoctrl.read_ip_addr(5100)[1]))
        citoctrl.close()
    else:
        print("Error: Unable to open connection to generator.")
