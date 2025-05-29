import random
import socket
import pygame
import pygame_helper

WHITE, BLACK = (255, 255, 255), (0, 0, 0)


class TicTacToe:
    board = []
    sign = ''
    enemy_sign = ''
    user_socket = None
    is_host = None
    screen = None
    unpacked_cell_rects = []
    WINDOW_X = None
    WINDOW_Y = None
    CROSS = None
    CIRCLE = None
    board_mostright = None
    board_mostbottom = None
    display_text = None
    recv_with_buttons = None
    leaving_room_screen = None

    def __init__(self, is_host, user_socket, who_first=None, screen=None):
        pygame.init()
        if screen is not None:
            self.screen = screen
            self.WINDOW_X, self.WINDOW_Y = screen.get_size()

        self.CROSS = pygame.image.load('cross.png').convert_alpha()
        self.CIRCLE = pygame.image.load('circle.png').convert_alpha()
        self.user_socket = user_socket
        self.init_board()
        cell_rects = self.print_board()
        self.unpacked_cell_rects = []
        for row in cell_rects:
            for cell in row:
                self.unpacked_cell_rects.append(cell)
        self.unpacked_cell_rects = tuple(self.unpacked_cell_rects)
        self.board_mostright, self.board_mostbottom = cell_rects[2][2].bottomright
        self.is_host = is_host

        # This imports functions from pygame_helper.
        pyhelper = pygame_helper.PyGameHelper(self.screen, self.WINDOW_X, self.WINDOW_Y, True, self.user_socket,
                                              self.board_mostright, self.board_mostbottom)
        self.display_text = pyhelper.display_text
        self.recv_with_buttons = pyhelper.recv_with_buttons
        self.leaving_room_screen = pyhelper.press_any_screen

        # if who_first == 0, server start, else, client start.
        if who_first is None:
            if is_host:
                who_first = random.randint(0, 1)
                self.user_socket.send(str(who_first).encode())
            else:
                who_first = self.user_socket.recv(1).decode()
                who_first = int(who_first)

        my_first = 0 if is_host else 1
        if who_first == my_first:
            self.sign = 'O'
            self.enemy_sign = 'X'
            self.place_mark()
        else:
            self.sign = 'X'
            self.enemy_sign = 'O'
            self.display_text('It\'s the other', 0, -15, 22)
            self.display_text('player\'s turn.', 0, 15, 22)
            pygame.display.flip()
            enemy_mark, _ = pyhelper.recv_with_buttons((), 2, lambda resp: resp is None)
            self.place_mark(enemy_mark)

    def place_mark(self, enemy_mark=None):
        pygame.event.clear()
        if enemy_mark is None:
            cell_rects = self.print_board()
            self.display_text('It\'s your turn.', 0, 0, 22)
            pygame.display.flip()

            x, y = -1, -1
            while x == -1 or y == -1:
                response, prsd_cell = self.recv_with_buttons(self.unpacked_cell_rects, 1)
                if response == '':
                    return self.leaving_room_screen('Other participent disconnected.')
                for j in range(3):
                    for i in range(3):
                        if cell_rects[i][j] == prsd_cell and self.board[i][j] == ' ':
                            x, y = i, j

            self.board[x][y] = self.sign
            self.user_socket.send(f'{x}{y}'.encode())
        else:
            if enemy_mark == '':
                return self.leaving_room_screen('Other participent disconnected.')
            try:
                x = int(enemy_mark[0])
                y = int(enemy_mark[1])
            except ValueError:
                return self.leaving_room_screen('Received invalid mark value.')
            else:
                self.board[x][y] = self.enemy_sign

        self.print_board()

        if self.is_game_won():
            return
        if enemy_mark is None:
            self.display_text('It\'s the other', 0, -15, 22)
            self.display_text('player\'s turn.', 0, 15, 22)
            pygame.display.flip()
            enemy_mark, _ = self.recv_with_buttons((), 2, lambda resp: resp is None)
            self.place_mark(enemy_mark)
        else:
            self.place_mark()

    # this functions checks if a player has won the game, prints the winner, and makes sure the game ends.
    def is_game_won(self):
        board = self.board
        board_can_be_full = True
        # x makes us check the board 4 times, one time for columns, one for rows, and 2 for the two diagonals.
        for x in range(4):
            j_range = 3 if x < 2 else 1
            # we use j and i to check every row on every y axis, every column on every x axis, and the two diagonals.
            for j in range(j_range):
                checking_sign = ''
                for i in range(3):
                    # this is how I choose whether to check for a column, a row, or a diagonal.
                    board_x, board_y = (i, j) if x == 0 else (j, i) if x == 1 else (i, i) if x == 2 else (i, 2 - i)
                    curr_mark = board[board_x][board_y]
                    # if the current mark is empty, we know that row or column can't win, so we break out of it.
                    if curr_mark == ' ':
                        board_can_be_full = False
                        break
                    # this defines the sign we're going to look for in this row or column
                    elif checking_sign == '':
                        checking_sign = curr_mark
                    # if we find a sign different to the first sign in the row or column we know that it can't be a win.
                    elif curr_mark != checking_sign:
                        break
                # if the for loop went successfully, then it will run this code, returning the winner's sign.
                else:
                    return self.after_game(checking_sign)
        else:
            if board_can_be_full:
                return self.after_game('Nobody')

    # this function prints who won, and implements the rematch feature.
    def after_game(self, winner_sign):
        self.print_board()

        if winner_sign == 'Nobody':
            self.display_text('Nobody', 0, -20)
            self.display_text('Won', 0, 20)
        else:
            sign = self.CROSS if winner_sign == 'X' else self.CIRCLE
            sign_width = self.WINDOW_Y * 0.09
            sign = pygame.transform.scale(sign, (sign_width, sign_width))
            self.display_text('Winner!', 0, -25)
            self.screen.blit(sign, (self.board_mostright + 130 - sign_width / 2, self.WINDOW_Y / 2))

        self.display_text('Rematch?', 0, 0, pos_to_board='b')
        yes_rect = self.display_text('Yes', -50, 50, pos_to_board='b')
        no_rect = self.display_text('No', 50, 50, pos_to_board='b')
        pygame.display.flip()

        response, prsd_button = self.recv_with_buttons((yes_rect, no_rect), 7)
        want_again = True if prsd_button == yes_rect else False if prsd_button == no_rect else None

        if want_again:
            alert = self.rematcher(winner_sign, response)
        elif want_again is False:
            alert = 'You declined the Rematch.'
        # if want_again is None then it means you didnt pick and yet got aborted which means the other guy disconnected.
        else:
            alert = 'Rematch Declined.'

        if alert is not None:
            self.leaving_room_screen(alert)
        return True

    def rematcher(self, winner_sign, response=None):
        self.user_socket.send('REMATCH'.encode())
        self.screen.fill(WHITE)
        self.display_text('Waiting for the opponent\'s', 0, -50, pos_to_board='c')
        self.display_text('rematch confirmation.', 0, 50, pos_to_board='c')
        quit_rect = self.display_text('Quit', self.WINDOW_X * 0.4, self.WINDOW_Y * -0.4, pos_to_board='c')
        pygame.display.flip()

        if response is None:
            response, _ = self.recv_with_buttons([quit_rect], 7, lambda data: data is None)

        # if the opponent also wants to REMATCH then you will both make sure you are READY and then start the game.
        if response == 'REMATCH':
            try:
                self.user_socket.send('READY'.encode())
            except (ConnectionResetError, ConnectionAbortedError):
                return 'Rematch declined.'
            else:
                response = self.user_socket.recv(5).decode()

            if response == 'READY':
                who_first = None
                if winner_sign == self.sign:
                    who_first = 0 if self.is_host else 1
                elif winner_sign == self.enemy_sign:
                    who_first = 1 if self.is_host else 0

                self.__init__(self.is_host, self.user_socket, who_first)
            else:
                return 'you should not be seeing this screen..'
        else:
            return 'Rematch declined.'

    # Initializes the board.
    def init_board(self):
        self.board = []
        for i in range(3):
            self.board.append([])
            [self.board[i].append(' ') for _ in range(3)]

    # Prints the board to the screen.
    def print_board(self):
        window_x, window_y = self.WINDOW_X, self.WINDOW_Y
        self.screen.fill(WHITE)

        width = window_y * 0.15
        padding = 10
        inner_width = width - padding

        cross = pygame.transform.scale(self.CROSS, (inner_width, inner_width))
        circle = pygame.transform.scale(self.CIRCLE, (inner_width, inner_width))

        cell_rect, x_pos, y_pos = None, None, None
        board_rects = [[] for _ in range(3)]
        for y in range(3):
            for x in range(3):
                cube_color, cube_width = BLACK, width
                for i in range(2):
                    x_pos = window_x / 2 - cube_width / 2 - width + (width - padding / 2) * x
                    y_pos = window_y / 2 - cube_width / 2 - width + (width - padding / 2) * y
                    cell_rect = pygame.draw.rect(self.screen, cube_color,
                                                 pygame.Rect(x_pos, y_pos, cube_width, cube_width))

                    cube_color, cube_width = WHITE, inner_width
                board_rects[x].append(cell_rect)

                curr_cell = self.board[x][y]
                if curr_cell != ' ':
                    sign = cross if curr_cell == 'X' else circle
                    self.screen.blit(sign, (x_pos, y_pos))
        pygame.display.flip()
        return board_rects


# TicTacToe(True, socket.socket(), screen=pygame.display.set_mode((800, 800)))
