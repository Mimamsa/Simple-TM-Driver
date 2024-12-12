import socket
import click
import time
import re

# ---- Low level functions ----

P_HEAD = b"\x24"  # $
P_END1 = b"\x0D"  # \r
P_END2 = b"\x0A"  # \n
P_SEPR = b"\x2C"  # ,
P_CSUM = b"\x2A"  # *


def checksum_xor(packet):
    """XOR characters over the entire string """
    cs = 0
    for el in packet:
        cs ^= el
    return cs


# ---- Mid-level functions ----

def gen_ptpj_payload(positions, velocity, acc_time, blend_percentage, final_goal):
    """Generate PTPJ script payload.
    Args
        positions (list[float,6]): Motion target. Expressed in joint angles, it includes 
            the angles of six joints: Joint1(°), Joint 2(°), Joint 3(°), Joint 4(°), Joint 5(°), Joint 6(°).
        velocity (int): The speed setting, expressed as a percentage (%)
        acc_time (int): The time interval to accelerate to top speed (ms)
        blend_percentage (int): Blending value, expressed as a percentage (%)
        final_goal (bool):
    Returns
        (bytes): resulting script.
    """
    final_goal_str = str(final_goal).lower()
    rounded_positions = list(map(lambda f: round(f,5), positions))

    # Generate PTPJ script
    payload = 'PTPJ,PTP(\"JPP\",{},{},{},{},{},{},{},{},{},{})'.format(
            *rounded_positions, velocity, acc_time, blend_percentage, final_goal_str
        ).encode()
    return payload


def gen_ptpc_payload(positions, velocity, acc_time, blend_percentage, final_goal):
    """Generate PTPC script payload.
    Args
        positions (list[float,6]): Motion target. Expressed in coordinate (w.r.t. current base), 
            it includes the tool end TCP relative motion value with respect to the specified coordinate: X 
            (mm), Y (mm), Z (mm), RX(°), RY(°), RZ(°)
        velocity (int): The speed setting, expressed as a percentage (%)
        acc_time (int): The time interval to accelerate to top speed (ms)
        blend_percentage (int): Blending value, expressed as a percentage (%)
        final_goal (bool):
    Returns
        (bytes): resulting payload.
    """
    final_goal_str = str(final_goal).lower()
    rounded_positions = list(map(lambda f: round(f,5), positions))

    # Generate PTPC script
    payload = 'PTPC,PTP(\"CPP\",{},{},{},{},{},{},{},{},{},{})'.format(
            *rounded_positions, velocity, acc_time, blend_percentage, final_goal_str
        ).encode()
    return payload


def gen_tool_coord_payload(transaction_id='01'):
    """Generate item request payload. '13' means item returns in JSON format.
    Args
        transaction_id (str): Should be 2 alphanumeric numbers [A-Z0-9].
    Returns
        (bytes): resulting payload
    """
    payload = "{},13,[{\"Item\":\"Coord_Robot_Tool\"}]".format(
            transaction_id
        ).encode()
    return payload


def wrap_tmsct_packet(payload):
    """Calculate checksum and wrap the script 
    Args
        script (bytes): TM script byte string.
    Returns
        (bytes): resulting packet.
    """
    sct_len = str(len(payload)).encode()
    script = b'TMSCT' + P_SEPR + sct_len + P_SEPR + payload + P_SEPR
    csum = checksum_xor(script)
    csum_str = '{:02x}'.format(csum).encode()
    packet = P_HEAD + script + P_CSUM + csum_str + P_END1 + P_END2
    return packet


def wrap_tmsvr_packet(payload):
    """Calculate checksum and wrap the script 
    Args
        script (bytes): TM script byte string.
    Returns
        (bytes): resulting packet.
    """
    sct_len = str(len(payload)).encode()
    script = b'TMSVR' + P_SEPR + sct_len + P_SEPR + payload + P_SEPR
    csum = checksum_xor(script)
    csum_str = '{:02x}'.format(csum).encode()
    packet = P_HEAD + script + P_CSUM + csum_str + P_END1 + P_END2
    return packet


def send_script(tm_sock, script):
    """Send script
    """
    # TODO: some verification for script and connection
    tm_sock.send(script)


# ---- High level functions ----

def move_joints(tmsct_sock, positions, velocity, acc_time, blend_percentage, final_goal):
    """Move robotic arm by setting joints.
    Args
        tmsct_sock (class 'socket.socket'): TMSCT socket.
    """
    payload = gen_ptpj_payload(positions, velocity, acc_time, blend_percentage, final_goal)
    packet = wrap_tmsct_packet(payload)
    print('Sending packet: ', packet)
    send_script(tmsct_sock, packet)


def move_coordinate(tmsct_sock, positions, velocity, acc_time, blend_percentage, final_goal):
    """Move robotic arm by setting coordinate and orientation (w.r.t current base).
    Args
        tmsct_sock (class 'socket.socket'): TMSCT socket.
    """
    payload = gen_ptpc_payload(positions, velocity, acc_time, blend_percentage, final_goal)
    packet = wrap_tmsct_packet(payload)
    print('Sending packet: ', packet)
    send_script(tmsct_sock, packet)


def stop_script(tmsct_sock):
    """StopAndClearBuffer(0) 
        Stop the robot motion immediately and clear the robot motion instructions in the buffer. """
    script_tag = b'1'
    payload = script_tag + b',StopAndClearBuffer(0)'
    packet = wrap_tmsct_packet(payload)
    print('Sending packet: ', packet)
    send_script(tmsct_sock, packet)


def get_tool_coord(tmsvr_sock):
    """Get TCP pose [X, Y, Z, Rx, Ry, Rz] in the world frame (robot base as origin)
    Args
        tmsvr_sock (class 'socket.socket'): TMSVR socket.
    Returns
        (list[6,float]): TCP pose [X, Y, Z, Rx, Ry, Rz] in the world frame (robot base as origin)
    """
    payload = gen_tool_coord_payload()
    packet = wrap_tmsvr_packet(payload)
    send_script(tmsvr_sock, packet)
    res = tmsvr_sock.recv(512)
    #print(res)  # b'$TMSVR,113,01,13,[{"Item":"Coord_Robot_Tool","Value":[-179.400269,343.784576,224.894272,-158.372284,-9.714196,-122.428917]}],*09\r\n'
    # TODO: Check whether responding is normal
    res = res.decode()
    m = re.search(r"(?<=\"Value\":\[).+(?=\]\}\])", res)
    ret = m[0].split(',')
    list(map(float, ret))
    return ret



@click.command()
@click.option('-ip', '--ip_address', default='', required=True, help='IP address of the robotic arm')
def main(ip_address):
    """Main loop """
    tmsct_port = 5890
    tmsvr_port = 5891

    # Connect to TMSCT
    #tmsct_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #tmsct_sock.connect((ip_address, tmsct_port))

    # Execute script
    #move_joints(tmsct_sock, [0, 0, 90, 0, 90, 0], 35, 200, 0, False)
    #res = tmsct_sock.recv(512)
    #print(res)

    # Connect to TMSVR
    tmsvr_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tmsvr_sock.connect((ip_address, tmsvr_port))
    
    # Send request
    # payload: transaction_id, mode, content => (id),13,[{"Item":"TCP_Value"}]
    # Joint_Angle, Coord_Robot_Flange, Coord_Robot_Tool, TCP_Value, TCP_Mass
    tcp_coord = get_tool_coord(tmsvr_sock)
    print(tcp_coord)

    #tmsct_sock.close()
    tmsvr_sock.close()


if __name__=='__main__':
    main()
