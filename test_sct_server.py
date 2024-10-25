import socket
import click
import time

@click.command()
@click.option('-ip', '--ip_address', default='127.0.0.1', help='IP address of the robotic arm')
def main(ip_address):

    tmsct_port = 5890
    # tmsvr_port = 5891

    # Start TMSCT server
    tmsct_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tmsct_sock.bind((ip_address, tmsct_port))
    tmsct_sock.listen(1)
    conn, addr = tmsct_sock.accept()
    with conn:
        print('Connected by', addr)
        while True:
            data = conn.recv(1024)
            print(data)
            conn.sendall(b'Response: '+ data)
            time.sleep(0.05)
    tmsct_sock.close()


if __name__=='__main__':
    main()