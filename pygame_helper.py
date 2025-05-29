import pygame
import socket

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)


class PyGameHelper:
    WINDOW_X, WINDOW_Y = None, None
    screen = None
    user_socket = None
    in_game = False
    board_mostright, board_mostbottom = None, None

    def __init__(self, screen, window_x, window_y, in_game, user_socket=None,
                 board_mostright=None, board_mostbottom=None):
        self.WINDOW_X, self.WINDOW_Y = window_x, window_y
        self.screen = screen
        self.in_game = in_game
        self.user_socket = user_socket
        self.board_mostright, self.board_mostbottom = board_mostright, board_mostbottom

    def display_text(self, text, x_offset, y_offset, size=32, color=BLACK, bg_color=None, pos_to_board='', center=True):
        font = pygame.font.Font('GothicA1-SemiBold.ttf', size)
        text_object = font.render(text, True, color, bg_color)
        text_rect = text_object.get_rect()
        if pos_to_board == '':
            pos_to_board = 'r' if self.in_game else 'c' if center else 'raw'

        if pos_to_board == 'r':
            text_rect.center = (self.board_mostright + 130 + x_offset, self.WINDOW_Y / 2 + y_offset)
        elif pos_to_board == 'b':
            text_rect.center = (self.WINDOW_X / 2 + x_offset, self.board_mostbottom + 50 + y_offset)
        elif pos_to_board == 'c':
            text_rect.center = (self.WINDOW_X / 2 + x_offset, self.WINDOW_Y / 2 + y_offset)
        elif pos_to_board == 'raw':
            text_rect.topleft = (x_offset, y_offset)

        self.screen.blit(text_object, text_rect)
        return text_rect

    def recv_with_buttons(self, button_rects, buf_size, running_cond=lambda x: True):
        self.user_socket.setblocking(False)
        pressed_button = None
        response = None

        pygame.event.clear()
        running = True
        while running_cond(response) and running:
            try:
                if response is None:
                    response = self.user_socket.recv(buf_size).decode()
                else:
                    tmp = self.user_socket.recv(1, socket.MSG_PEEK).decode()
                    if tmp == '':
                        response = ''
            except BlockingIOError:
                pass

            if response == '':
                break

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    for button_rect in button_rects:
                        if button_rect.collidepoint(mouse_x, mouse_y):
                            pressed_button = button_rect
                            running = False
                            break

        self.user_socket.setblocking(True)

        return response, pressed_button

    def press_any_screen(self, alert, post_alert='Press any key to continue.'):
        if self.in_game:
            self.user_socket.close()
        self.screen.fill(WHITE)
        self.display_text(alert, 0, -50, pos_to_board='c')
        self.display_text(post_alert, 0, 50, pos_to_board='c')
        pygame.display.flip()

        pygame.event.clear()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    return
