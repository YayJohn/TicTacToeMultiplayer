import socket
import pyperclip
import pygame
from TicTacToe import TicTacToe
import pygame_helper

BROWSER_PORT = 6010
BLACK, WHITE = (0, 0, 0), (255, 255, 255)

WINDOW_X, WINDOW_Y = 800, 800

pygame.init()
screen = pygame.display.set_mode((WINDOW_X, WINDOW_Y))

pyhelper = pygame_helper.PyGameHelper(screen, WINDOW_X, WINDOW_Y, False)
display_text = pyhelper.display_text
recv_with_buttons = pyhelper.recv_with_buttons
press_any_screen = pyhelper.press_any_screen


def main():
    press_any_screen('Welcome to my Tic Tac Toe game!')

    # ask for the browser ip, and check if it actually has a server browser listening to it.
    browser_ip = gui_input('Whats the server browser server\'s IP?', is_host_alive, 'Failed to connect to the server')
    # browser_ip = '127.0.0.1'
    nickname = gui_input('Choose a nickname.')

    screen.fill(WHITE)
    refresh_rect = display_text('Refresh', WINDOW_X * 0.3, -50, 42)
    host_rect = display_text('Host', WINDOW_X * 0.3, 50, 42)

    padding = WINDOW_Y * 0.02
    browser_rect = pygame.Rect(padding, padding, WINDOW_X * 0.6, WINDOW_Y * 0.96)
    pygame.draw.rect(screen, BLACK, browser_rect)
    pygame.display.flip()

    rooms = []
    room_rects = []
    re_print = False
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                if refresh_rect.collidepoint(mouse_x, mouse_y):
                    rooms = get_all_rooms(browser_ip)

                    pygame.draw.rect(screen, BLACK, browser_rect)
                    offset = 12
                    room_rects = []
                    if rooms is not None:
                        for room in rooms:
                            room_rect = display_text(room[1], padding+22, padding+10+offset,
                                                     size=28, color=WHITE, center=False)
                            room_rects.append(room_rect)
                            offset += 50
                    pygame.display.flip()

                elif host_rect.collidepoint(mouse_x, mouse_y):
                    host_room(browser_ip)
                    re_print = True
                else:
                    for i, room_rect in enumerate(room_rects):
                        if room_rect.collidepoint(mouse_x, mouse_y):
                            connect_to_room(rooms[i], browser_ip, nickname)
                            re_print = True
                            break

                if re_print:
                    screen.fill(WHITE)
                    refresh_rect = display_text('Refresh', WINDOW_X * 0.3, -50, 42)
                    host_rect = display_text('Host', WINDOW_X * 0.3, 50, 42)
                    pygame.draw.rect(screen, BLACK, browser_rect)
                    pygame.display.flip()
                    re_print = False


# get_all_rooms requests all the rooms in the server browser and prints them too.
def get_all_rooms(browser_ip):
    with socket.socket() as search_socket:
        search_socket.settimeout(3)
        search_socket.connect((browser_ip, BROWSER_PORT))
        search_socket.send('REFRESH'.encode())
        rooms = search_socket.recv(1024).decode()
        if rooms == '':
            return

        rooms = rooms.split('\r\n')
        # rooms is a list of all the rooms, and it has an additional empty list at the end, so i delete it.
        rooms.pop(len(rooms)-1)
        for i in range(len(rooms)):
            # noinspection PyTypeChecker
            rooms[i] = rooms[i].split(maxsplit=1)
            # room = [room_id, room_name]
        return rooms


def connect_to_room(room, browser_ip, nickname):
    screen.fill(WHITE)
    display_text('Connecting..', 0, 0)
    quit_rect = display_text('Quit', WINDOW_X * 0.4, WINDOW_Y * -0.4)
    pygame.display.flip()

    room_id = room[0]
    with socket.socket() as user_socket:
        user_socket.connect((browser_ip, BROWSER_PORT))
        user_socket.send(f'CONNECT {room_id} {nickname}'.encode())

        screen.fill(WHITE)
        display_text('Waiting for the host to accept you.', 0, 0)
        display_text('Quit', WINDOW_X * 0.4, WINDOW_Y * -0.4)
        pygame.display.flip()

        pyhelper.user_socket = user_socket
        response, quit_prsd = recv_with_buttons((quit_rect,), 7, lambda resp: resp is None)

        if response == 'ACCEPT':
            user_socket.send('READY'.encode())
            TicTacToe(False, user_socket, screen=screen)
        elif response == 'DECLINE':
            press_any_screen('You got declined by the room host.')
        elif response == 'INGAME':
            press_any_screen('The game had already started.')


# Hosts a game room.
def host_room(browser_ip):
    room_name = gui_input('Enter a name for your Room', lambda name: not name.isspace(),
                          err_alert='room name cannot be empty.', can_quit=True)

    # if room_name is None it means the user quit the input and so doesn't wish to host a room anymore.
    if room_name is None:
        return

    with socket.socket() as room_socket:
        room_socket.connect((browser_ip, BROWSER_PORT))

        command = f'HOST {room_name}'
        room_socket.send(command.encode())
        response = room_socket.recv(1).decode()
        if response == '0':
            press_any_screen('A room already exists with this name.')
            host_room(browser_ip)
            return

        screen.fill(WHITE)
        display_text('Waiting for a player to log in..', 0, 0)
        quit_rect = display_text('Quit', WINDOW_X*0.4, WINDOW_Y*-0.4)
        pygame.display.flip()

        padding = WINDOW_Y * 0.05
        pyhelper.user_socket = room_socket
        # lobby_user = (user_id, user_nickname)
        lobby_users = []
        user_accepts = []
        user_declines = []
        while True:
            data, prsd_button = recv_with_buttons(user_accepts + user_declines + [quit_rect], 1024, lambda x: x is None)

            if prsd_button is quit_rect or data == '':
                break
            elif prsd_button is not None:
                if prsd_button in user_accepts:
                    user_index = user_accepts.index(prsd_button)
                    user_id = lobby_users[user_index][0]
                    room_socket.send(f'ACCEPT {user_id}'.encode())

                    response = room_socket.recv(5).decode()
                    if response == 'READY':
                        pygame.event.clear()
                        TicTacToe(True, room_socket, screen=screen)
                        return
                else:
                    user_index = user_declines.index(prsd_button)
                    user_id = lobby_users[user_index][0]
                    room_socket.send(f'DECLINE {user_id}'.encode())
                    lobby_users.pop(user_index)
                    data = 'no_data'

            data = data.split(maxsplit=2)
            print(data)
            if data[0] == 'CONNECT':
                user_id, user_nickname = data[1], data[2]
                lobby_users.append((user_id, user_nickname))
            elif data[0] == 'LEFT':
                user_id = data[1]
                for i, lobby_user in enumerate(lobby_users):
                    if lobby_user[0] == user_id:
                        user_index = i
                        lobby_users.pop(user_index)
                        break

            user_accepts = []
            user_declines = []
            offset = 12
            screen.fill(WHITE)
            for user in lobby_users:
                user_nickname = user[1]
                user_rect = display_text(user_nickname, padding+22, padding+10+offset, 30, center=False)
                x_offset = user_rect.bottomright[0]
                user_accept = display_text('Accept', x_offset + 50, padding+10+offset, 30, (0, 205, 0), center=False)
                x_offset = user_accept.bottomright[0]
                user_decline = display_text('Decline', x_offset + 40, padding+10+offset, 30, (255, 0, 0), center=False)

                user_accepts.append(user_accept)
                user_declines.append(user_decline)
                offset += 50
            pygame.display.flip()


def is_host_alive(address):
    address_no_dots = address.replace('.', '')
    if len(address) != len(address_no_dots) + 3 or address_no_dots.isdigit() is False:
        return False
    with socket.socket() as check_socket:
        check_socket.settimeout(2)
        try:
            check_socket.connect((address, BROWSER_PORT))
            check_socket.send('CHECK'.encode())
            response = check_socket.recv(5).decode()
        except (socket.timeout, ConnectionRefusedError, socket.gaierror) as exception:
            print(f'THE EXCEPTION: {exception}\n')
            return False
        else:
            return True if response == "ALIVE" else print('Server Browser returned unexpected statement.')


# TODO: make shift work, for letters like !
def gui_input(alert, valid_checker=lambda x: True, err_alert='Error', can_quit=False):
    input_string = ''
    quit_rect = None
    do_print = True
    running = True
    while running:
        if do_print:
            screen.fill(WHITE)
            display_text(alert, 0, -50)
            display_text(input_string, 0, 50)
            if can_quit:
                quit_rect = display_text('Quit', WINDOW_X*0.4, WINDOW_Y*-0.4)
            pygame.display.flip()
            do_print = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
            elif can_quit and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                if quit_rect.collidepoint(mouse_x, mouse_y):
                    return
            elif event.type == pygame.KEYDOWN:
                if event.key != pygame.K_RETURN:
                    if event.key == pygame.K_BACKSPACE:
                        input_string = input_string[:-1]
                    elif event.key == pygame.K_SPACE:
                        input_string += ' '
                    else:
                        key_string = pygame.key.name(event.key)
                        if len(key_string) == 1:
                            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                                key_string = key_string.upper()
                            elif pygame.key.get_mods() & pygame.KMOD_CTRL and key_string == 'v':
                                key_string = pyperclip.paste()
                            input_string += key_string

                    do_print = True
                else:
                    if input_string == '':
                        display_text('Invalid Value', 0, 100)
                        pygame.display.flip()
                        continue

                    display_text('Working..', 0, 100)
                    pygame.display.flip()

                    if valid_checker(input_string):
                        screen.fill(WHITE)
                        pygame.display.flip()
                        return input_string
                    else:
                        input_string = ''
                        press_any_screen(err_alert, 'Try Again.')
                        do_print = True


if __name__ == '__main__':
    main()

# TODO: Make a lobby
# TODO: Tidy up the code a bit
# TODO: add button feedback on press, and make it so the button script runs on MouseButtonUp
