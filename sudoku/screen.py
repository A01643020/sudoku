"""Clases para la renderización y administración de pantallas de tamaño completo en la consola."""

import sys
from .terminal import get_terminal
from .sudoku import Sudoku
from .utils import is_key_directional
from .characters import CHAR_FONTS

term = get_terminal()

class SudokuScreen():
    """Pantalla principal con el juego de Sudoku."""
    def __init__(self, grade, difficulty):
        self.term_width = term.width
        self.term_height = term.height
        self.grade = grade
        self.difficulty = difficulty
        self.cursor_pos = [0, 0] # La posición del cursor respectivo a las celdas del Sudoku.
        self.sud = Sudoku(grade, difficulty)
        self.edited_cell = False # Bandera que indica si se editó una celda

    def render(self):
        """Ciclo principal de la pantalla. Dibuja el tablero y otros elementos a la pantalla."""
        with term.fullscreen(), term.cbreak():
            with term.hidden_cursor():
                self.draw_sudoku(numbers=False)
                self.draw_subtitle('Cargando...')
                # Generamos un nuevo sudoku aleatorio, quitamos el mensaje de cargar, y actualizamos la pantalla
                self.sud.generate_sudoku()
                self.clear_subtitle()
                self.draw_sudoku(grid=False) # Dibujamos sólo los números del Sudoku
                # Mover el cursor a la primera celda modificable, para el punto de partida del cursor
                col, row = self.sud.get_next_modifiable_cell(0, 0, 1, True)
                self.cursor_pos = [col, row]
                # Calculamos las coordenadas reales del cursor si estuviera en la celda que calculamos
                col, row = self.calc_cursor_pos(col, row)
                sys.stdout.write(term.move_xy(col, row))
                sys.stdout.flush()

            while True:
                # En caso de que la consola cambió de tamaño volvemos a dibujar todo
                if self.changed_size():
                    sys.stdout.write(term.clear)
                    self.draw_sudoku()

                ##### CONTROLES #####
                # Esta sección se dedica a lidiar con las teclas del usuario, para manipular e interactuar con el juego
                key = term.inkey()
                # Si la tecla presionada es un número, sea del teclado principal o el keypad
                if (n := key).isnumeric() or (n := key).replace('KEY_KP_', '').isnumeric():
                    num = int(n)
                    if num > self.sud.size:
                        continue # El número está fuera de rango
                    col, row = self.cursor_pos
                    # Cambiar el número en el tablero si es modificable
                    if self.sud.given[row][col] == 0:
                        self.sud.content[row][col] = num
                        self.sud.correct[row][col] = None
                        self.edited_cell = True
                    else:
                        continue
                # Este caso trata con el movimiento del cursor
                elif is_key_directional(key):
                    self.update_numbers(col, row)
                    col, row = self.handle_move(key)
                    # Hacemos flush para que el cursor se mueva immediatamente, y no tengamos que renderizar todo
                    # el tablero cada vez que cambiemos celda
                    self.move_cursor_to(col, row, flush=True)
                    continue # esto se salta self.draw_sudoku()
                # En caso de presionar Backspace o Delete, borrar la celda y actualizar el estado interno
                elif key.code in (term.KEY_BACKSPACE, term.KEY_DELETE):
                    col, row = self.cursor_pos
                    # Cambiar el número en el tablero si es modificable
                    if self.sud.given[row][col] == 0:
                        self.sud.content[row][col] = 0
                    self.edited_cell = True
                    self.update_numbers(col, row)
                # Shift+Delete borra todo el tablero, regresándolo a su estado inicial
                elif key.code == term.KEY_SDC:
                    # Borrar todo el tablero
                    for i in range(self.sud.size):
                        for j in range(self.sud.size):
                            self.sud.content[i][j] = self.sud.given[i][j]
                            self.sud.correct[i][j] = None
                # La tecla Enter guarda el valor de la celda y comunica si estaba correcto o incorrecto
                elif key.code == term.KEY_ENTER:
                    self.update_numbers(col, row)
                    col, row = self.cursor_pos
                    # col, row = self.sud.get_next_modifiable_cell(col, row, 1)
                    self.move_cursor_to(col, row, flush=True)
                    continue # esto se salta self.draw_sudoku()
                # La tecla q o Escape sale del juego
                elif key == 'q' or key.code == term.KEY_ESCAPE:
                    break
                else:
                    # Si cualquier otra tecla es presionada, regresar al principio del loop (para ahorrarnos
                    # dibujar el sudoku cuando nadia haya cambiado)
                    continue

                # Sólo es necesario renderizar los números
                self.draw_sudoku(grid=False)

        self.stop()

    def update_numbers(self, col, row):
        """Actualizar los números y si están correctos o no."""
        # Revisar números, colorear números correctos/incorrectos si es necesario
        # Sólo sucede si se editó un número
        if self.edited_cell:
            self.sud.update_conflicts(col, row)
            self.draw_sudoku(grid=False)
            self.edited_cell = False # Resetear bandera

    def handle_move(self, key):
        """Mueve el cursor de acuerdo a la tecla del teclado presionada."""
        (x, y) = self.cursor_pos
        # flecha: mover celda
        if key.code == term.KEY_UP or key == 'w':
            y = (y - 1) % self.sud.size
        elif key.code == term.KEY_DOWN or key == 's':
            y = (y + 1) % self.sud.size
        elif key.code == term.KEY_LEFT or key == 'a':
            x = (x - 1) % self.sud.size
        elif key.code == term.KEY_RIGHT or key == 'd':
            x = (x + 1) % self.sud.size
        # Shift + flecha: Buscar la siguiente celda editable
        elif key.code == term.KEY_SUP or key == 'W':
            x, y = self.sud.get_next_modifiable_cell(x, y, 0)
        elif key.code == term.KEY_SRIGHT or key == 'D':
            x, y = self.sud.get_next_modifiable_cell(x, y, 1)
        elif key.code == term.KEY_SDOWN or key == 'S':
            x, y = self.sud.get_next_modifiable_cell(x, y, 2)
        elif key.code == term.KEY_SLEFT or key == 'A':
            x, y = self.sud.get_next_modifiable_cell(x, y, 3)

        return x, y

    def move_cursor_to(self, x, y, flush=False):
        """Mueve el cursor a la celda (x, y), calculando su posición real y haciendo flush a la consola si es especificado."""
        self.cursor_pos = [x, y]
        col, row = self.calc_cursor_pos(x, y)
        sys.stdout.write(term.move_xy(col, row))
        if flush:
            sys.stdout.flush()

    def draw_sudoku(self, grid=True, numbers=True):
        """Renderiza el tablero de Sudoku a la pantalla."""
        with term.location():
            if self.changed_size():
                # Las dimensiones de la consola cambiaron, volver a dibujar
                sys.stdout.write(term.clear)
            (sudoku_width, sudoku_height) = self.sud.rendered_size()
            # Imprimir un error si el tablero de sudoku no cabe en la consola
            if sudoku_height > self.term_height or sudoku_width > self.term_width:
                sys.stdout.write(term.move_down(term.height//2 - 1))
                sys.stdout.write(term.center(term.red('ERROR ') + 'La consola es demasiado pequeña para dibujar el tablero.'))
                sys.stdout.write(term.center(f'Favor de extender la consola al menos {sudoku_height-self.term_height} filas'))
                sys.stdout.flush()
                return
            if grid:
                sys.stdout.write(term.home)
                sys.stdout.write(term.move_down((term.height - sudoku_height)//2))
                # Imprimir tablero vacío
                for line in self.sud.render(show_nums=False):
                    sys.stdout.write(term.center(line))
            if numbers:
                # Mover el cursor a la primera celda
                sys.stdout.write(term.home)
                # Esta variable guardará si todos los números son correctos
                correct = True
                for i in range(self.sud.size):
                    for j in range(self.sud.size):
                        (cell_x, cell_y) = self.calc_cursor_pos(j, i)
                        sys.stdout.write(term.move_xy(cell_x, cell_y))
                        # Mantener un inventario de las celdas, para checar si todo el tablero está correcto
                        cell_correct = self.sud.correct[i][j]
                        # Verificar si la celda es correcta, y no está vacía
                        correct = correct and cell_correct and self.sud.content[i][j] != 0
                        # Es el número en esta celda uno predeterminado o escrito por el usuario?
                        if (n := self.sud.given[i][j]) == 0:
                            n = self.sud.content[i][j]
                            color = term.normal
                            if cell_correct is True:
                                color = term.palegreen
                            elif cell_correct is False:
                                color = term.lightcoral
                            sys.stdout.write(color + CHAR_FONTS['alpha'][n] + term.normal)
                        else:
                            color = term.slategray4
                            if cell_correct is False:
                                color = term.firebrick4
                            sys.stdout.write(color + CHAR_FONTS['alpha'][n] + term.normal)

                if correct:
                    if self.sud.is_solved():
                        self.draw_subtitle('LO LOGRASTEEE')

            sys.stdout.flush()

    def draw_subtitle(self, text):
        """Dibuja un texto de subtítulo en la parte inferior de la pantalla."""
        with term.location():
            # El texto debe de estar a la mitad del espacio entre el sudoku y el borde inferior de la consola
            sys.stdout.write(term.home + term.move_down(term.height - (term.height - self.sud.rendered_size()[1])//4))
            sys.stdout.write(term.center(text))

    def clear_subtitle(self):
        """Borra el subtítulo de la pantalla."""
        with term.location():
            sys.stdout.write(term.home + term.move_down(term.height - (term.height - self.sud.rendered_size()[1])//4))
            sys.stdout.write(term.clear_eol)

    def changed_size(self):
        """Verificar si cambió el tamaño de la consola."""
        w = term.width
        h = term.height
        if w != self.term_width or h != self.term_height:
            # Cambiaron, actualizar las variables y regresar verdadero
            self.term_width = w
            self.term_height = h
            return True
        # Las dimensiones no han cambiado
        return False

    def calc_cursor_pos(self, x, y):
        """Regresa la posición del cursor si estuviera en la celda Sudoku x, y. La celda 0, 0 tiene la posición 0,0."""
        (sudoku_width, sudoku_height) = self.sud.rendered_size()
        return (x*4 + (term.width-sudoku_width)//2+2, y*2 + (term.height-sudoku_height)//2+1)

    # pylint: disable=missing-function-docstring
    def stop(self):
        pass
        # print("done!")