import socket
import threading
from time import sleep

BROWSER_PORT = 6010

rooms = []
hosts = []
users = []


def main():
    with socket.socket() as server_socket:
        server_socket.bind(('0.0.0.0', BROWSER_PORT))
        server_socket.listen()
        connection_thread = threading.Thread(target=handle_connection, args=(server_socket,))
        connection_thread.start()
        print('Listening..')
        while threading.active_count() > 0:
            sleep(5)


def handle_connection(server_socket):
    user_socket, address = server_socket.accept()

    connection_thread = threading.Thread(target=handle_connection, args=(server_socket,))
    connection_thread.start()

    data = user_socket.recv(1024).decode()

    response = handle_exchange(data, user_socket)
    if response is not None:
        user_socket.send(response.encode())

    user_socket.close()


def handle_exchange(data, user_socket):
    data = data.split(maxsplit=1)
    request = data[0]

    if request == 'HOST':
        # 1 tells to the host pc that the room name is available, 0 tells that it's not.
        if is_host_name_valid(data):
            room_name = data[1]
            user_socket.send('1'.encode())

            proxy_func(room_name, user_socket, True)
        else:
            user_socket.send('0'.encode())
            return

    elif request == 'CONNECT':
        # request = 'CONNECT room_id nickname'
        requested_room, nickname = data[1].split(maxsplit=1)
        proxy_func((requested_room, nickname), user_socket, False)

    elif request == 'REFRESH':
        hosts_string = ''
        for i, room_name in enumerate(rooms):
            if room_name is not None:
                hosts_string += '{} {}\r\n'.format(i, room_name)

        return hosts_string

    elif request == 'CHECK':
        return 'ALIVE'


def is_host_name_valid(data):
    try:
        room_name = data[1]
    except IndexError:
        return False

    for room in rooms:
        if room == room_name:
            return False
    else:
        return True


def proxy_func(parameter, user_socket, is_host):
    room_name, connected, user_id, waiting_users = [None] * 4
    if is_host:
        room_name = parameter
        room_id = len(hosts)
        rooms.append(room_name)
        hosts.append([])
        waiting_users = []
        connected = False
        print(f'{room_id}: "{room_name}" added!')
    else:
        user_id = len(users)
        users.append([])
        room_id = int(parameter[0])
        nickname = parameter[1]
        hosts[room_id].append(f'CONNECT {user_id} {nickname}')

    my_proxy, other_proxy = (hosts, users) if is_host else (users, hosts)
    my_id, other_id = (room_id, None) if is_host else (user_id, None)
    while True:
        if len(my_proxy[my_id]) > 0:
            exchange = my_proxy[my_id][0]
            if is_host:
                if exchange[:7] == 'CONNECT':
                    tmp_user = int(exchange.split()[1])
                    if connected:
                        users[tmp_user].append('INGAME')
                        hosts[room_id].pop(0)
                        continue
                    else:
                        waiting_users.append(tmp_user)
                elif exchange[:4] == 'LEFT' and connected:
                    my_proxy[my_id].pop(0)
                    continue
                elif exchange == 'READY' and not connected:
                    connected = True
                    rooms[room_id] = None
                    waiting_users.remove(other_id)
                    for waiting_user in waiting_users:
                        users[waiting_user].append('DECLINE')
                    print(f'room {room_id} had connected to {other_id}')
                elif exchange == 'DISCONNECT':
                    rooms[my_id], hosts[room_id] = None, None
                    print(f'{my_id}: "{room_name}" removed.')
                    return
            else:
                if exchange == 'ACCEPT':
                    other_id = room_id
                    print(f'user {user_id} connected to room {room_id}')
                elif exchange == 'INGAME':
                    print(f'user {user_id} declined from room {room_id}, because of INGAME')
                    users[user_id] = None
                    user_socket.send(exchange.encode())
                    return
                elif exchange == 'DISCONNECT':
                    users[user_id] = None
                    print(f'user {user_id} disconnected from room {room_id}')
                    return

            user_socket.send(exchange.encode())
            my_proxy[my_id].pop(0)
        else:
            user_socket.setblocking(False)
            response = None
            while response is None:
                try:
                    response = user_socket.recv(1024).decode()
                    if response == '':
                        raise ConnectionResetError
                except ConnectionResetError:
                    if is_host:
                        rooms[room_id], hosts[room_id] = None, None
                        for waiting_user in waiting_users:
                            users[waiting_user].append('DISCONNECT')
                        print(f'{room_id}: "{room_name}" removed.')
                    else:
                        users[user_id] = None
                        print(f'user {user_id} disconnected from room {room_id}')
                    if other_id is not None:
                        other_proxy[other_id].append('DISCONNECT')
                    elif not is_host and other_proxy[room_id] is not None:
                        other_proxy[room_id].append(f'LEFT {user_id}')
                    return
                except BlockingIOError:
                    if len(my_proxy[my_id]) > 0:
                        break
                else:
                    if is_host:
                        response = response.split()
                        if response[0] == 'ACCEPT':
                            other_id = int(response[1])
                            response = response[0]
                        elif response[0] == 'DECLINE':
                            other_proxy[int(response[1])].append(response[0])
                            continue
                        else:
                            response = ' '.join(response)
                    other_proxy[other_id].append(response)
            user_socket.setblocking(True)


if __name__ == '__main__':
    main()
