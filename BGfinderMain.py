import sys
import io
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QGridLayout, QPushButton, QWidget, QScrollArea, \
    QLabel, QButtonGroup
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5 import uic
import sqlite3
import time


class EmptySqlResult(Exception):  # класс исключения на случай если ничего не найдено
    def __init__(self, string):
        if not string:
            self.__str__()

    def __str__(self):
        return 'ERROR: Nothing found'


class WrongName(Exception):  # класс исключения на случай если введенное название игры неверно
    def __init__(self, name):
        self.name = name
        self.names = db.cur.execute('select name from data').fetchall()
        if not self.in_names():
            self.possible_results()

    def in_names(self):
        """
        the function checks whether at least one game name from the database matches the one entered
        :return: bool
        """
        return any([i[0] == self.name for i in self.names])

    def __str__(self):
        if not self.in_names():
            return 'ERROR: Wrong name'
        return ''

    def possible_results(self):
        """
        the function checks if there are games with a similar name in the database
        :return: None
        """
        possible_names = list()
        for name in self.names:
            possible_set = set(name[0] + self.name)
            s = 0
            for i in possible_set:
                if i in name[0] and i in self.name:
                    s += 1
            if s / len(possible_set) * 100 > 50 or name[0] in self.name:
                possible_names.append(name[0])

        print(f'Возможно вы имели ввиду {", ".join(possible_names)}?' if possible_names else 'Ничего не найдено')
        if not self.in_names() and possible_names:
            ex.create_dialog(possible_names[0])


class DatabaseQuery:
    def __init__(self):
        self.con = sqlite3.connect('mybase.db')
        self.cur = self.con.cursor()

    def query_generator(self, *values):
        """
        the function generates and returns an sql query
        :param values: tuple
        :return: str
        """
        game_diff, player_count, rec_age, game_time, game_name, favorite = values

        dif_str = self.difficulty_sql_generate(game_diff)  # по кусочкам собирает sql запрос
        pl_str = self.players_sql_generate(dif_str, player_count)
        age_str = self.age_sql_generate(dif_str, pl_str, rec_age)
        tm_str = self.time_sql_generate(dif_str, pl_str, age_str, game_time)
        nm_str = self.name_sql_generate(dif_str, pl_str, age_str, tm_str, game_name)
        fav_str = self.is_favorite_generate(dif_str, pl_str, age_str, tm_str, game_name, favorite)

        self.print_sql_to_console(f'''select * from data
                  {('where ' if dif_str + pl_str + age_str + tm_str + nm_str + fav_str else '') + dif_str + pl_str
                   + age_str + tm_str + nm_str + fav_str}\n''')

        result = self.cur.execute(f'''select * from data
                                      {('where ' if dif_str + pl_str + age_str + tm_str + nm_str + fav_str else '') +
                                       dif_str + pl_str + age_str + tm_str + nm_str + fav_str}''').fetchall()
        try:
            if game_name != '':
                raise WrongName(game_name)  # проверка исключения неправильного имени
        except WrongName:
            print('Wrong game name')
        try:
            if not result:
                raise EmptySqlResult(result)  # проверка исключения пустого результата
        except EmptySqlResult:
            print('Nothing found')
            if not self.new_name_in_names(ex.game_name.text(),
                                          self.cur.execute('''select name from data''').fetchall()):
                ex.scroll_clear()
        return result

    def new_name_in_names(self, name, sql):  # проверяет есть ли измененное имя в бд
        """
        the function checks if there is a new installed game name among the game names from the database
        :param sql: list
        :param name: str
        :return: bool
        """
        print(name in [i[0] for i in sql])
        return name in [i[0] for i in sql]

    def print_sql_to_console(self, sql):
        """
        the function outputs the generated sql query to the console
        :param sql: str
        :return: None
        """
        print(sql)

    def difficulty_sql_generate(self, difficulty):
        """
        the function generates the part of the sql query responsible for the difficulty of the game
        :param difficulty: str
        :return: str
        """
        if difficulty != 'Любая':
            return f'''difficulty = (select ind from difficulties
            where difficulty = "{difficulty}") '''
        return ''

    def players_sql_generate(self, difficulty, player_count):
        """
        the function generates the part of the sql query responsible for the number of players for the game
        :param difficulty: str
        :param player_count: str
        :return: str
        """
        if player_count != 0:
            return f'{"" if not difficulty else "and "}players_min <= {player_count} and players_max >= {player_count} '
        return ''

    def age_sql_generate(self, difficulty, player_count, rec_age):
        """
        the function generates the part of the sql query responsible for the age limit of the players
        :param difficulty: str
        :param player_count: str
        :param rec_age: str
        :return: str
        """
        if rec_age != 'Для всех возрастов':
            return f'{"" if not difficulty and not player_count else "and "}age > {int(rec_age[:-1]) - 1} '
        return ''

    def time_sql_generate(self, difficulty, player_count, rec_age, game_time):
        """
        the function generates the part of the sql query responsible for the time of one game party
        :param difficulty: str
        :param player_count: str
        :param rec_age: str
        :param game_time: str
        :return: str
        """
        if game_time != 0:
            return f'{"" if not difficulty and not player_count and not rec_age else "and "}' \
                   f'max_time >= {game_time} and min_time <= {game_time} '
        return ''

    def name_sql_generate(self, difficulty, player_count, rec_age, game_time, game_name):
        """
        the function generates the part of the sql query responsible for the name of the game
        :param difficulty: str
        :param player_count: str
        :param rec_age: str
        :param game_time: str
        :param game_name: str
        :return: str
        """
        if game_name != '':
            condition = "" if not difficulty and not player_count and not rec_age and not game_time else "and "
            return f'{condition}name = "{game_name}"'
        return ''

    def is_favorite_generate(self, difficulty, player_count, rec_age, game_time, game_name, is_favorite):
        """
        the function generates the part of the sql query responsible for the name of the game
        :param difficulty: str
        :param player_count: str
        :param rec_age: str
        :param game_time: str
        :param game_name: str
        :param is_favorite: bool
        :return: str
        """
        if is_favorite:
            condition = ("" if not difficulty and not player_count and not rec_age and not game_time and
                               not game_name else "and ")
            return f'{condition}favorite = "1"'
        return ''

    def get_favorite(self, name):  # функция возвращает 1 или 0 в зависимости от того находится ли игра в избранном
        """
        the function returns 1 or 0 depending on whether the game is in favorites
        :param name: str
        :return: int
        """
        return self.cur.execute(f'''select favorite from data 
                                    where name = "{name}"''').fetchall()  # -> число 1 или 0 избранное или нет

    def set_favorite(self, name, is_favorite):  # меняет бд, добавляет игру в избранное
        """
        the function changes the database by adding the game to favorites
        :param name: str
        :param is_favorite: int
        :return:
        """
        self.cur.execute(f'''update data
                           set favorite = {1 if is_favorite == 0 else 0}
                           where name = "{name}"''').fetchall()
        self.con.commit()


class BGFWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        f = io.StringIO(open('BGFinder_design0.2.1.ui', encoding='utf8').read())  # загружает дизайн
        uic.loadUi(f, self)
        self.add_values_to_sort()  # устанавливает значения в некоторые виджеты
        self.not_statusbar = bool()
        self.buttons_group = QButtonGroup(self)
        self.timer = 0
        self.statusBar()
        self.init_ui()

    def init_ui(self):
        """
        the function sets the name of the window and fixes its size
        :return: None
        """
        self.setWindowTitle('BGFinder0.2.1')
        self.setFixedSize(800, 600)
        self.setWindowIcon(QIcon('images/icon.jpg'))
        self.find_button.clicked.connect(self.find_games)  # подключает функцию к кнопке поиска
        self.game_time.valueChanged.connect(self.changed_game_time)

    def changed_game_time(self):  # устанавливает значение scroller-а (количество игроков) в label
        """
        the function sets the number of players to search in the label
        :return: None
        """
        self.time_label.setText(f'{self.game_time.value()}')

    def find_games(self):
        """
        the function executes a search query and passes the data to the function for output
        :return: None
        """
        self.timer = time.time()
        self.print_timer(round(time.time() - self.timer, 2), 'Поиск')  # вывод таймера
        self.plain_text(db.query_generator(self.game_diff.currentText(), self.player_count.value(),
                                           self.rec_age.currentText(), self.game_time.value(),
                                           self.game_name.text(), self.favoriteCheckbox.isChecked()))

    def add_values_to_sort(self):  # добавляет значения в виджет возраста для сортировки
        """
        the function sets values to age widget for sorting
        :return: None
        """
        for i in sorted(db.cur.execute('''select distinct age from data''').fetchall()):  # устанавливает возраст
            self.rec_age.addItem(f'{str(i[0])}+')

    def find_by_name(self, name: str):  # вызывается только при диалоговом окне
        """
        the function changes the name of the game with an error to search ONLY BY NAME
        :param name: str
        :return: None
        """
        self.game_name.setText(name)  # устанавливает имя, которое было исправлено
        self.clear_finder_values()
        self.find_games()  # поиск игр

    def clear_finder_values(self):  # устанавливает первоначальные значения в переменные
        """
        the function sets the initial values to widgets for sorting
        :return: None
        """
        self.game_diff.setCurrentText('Любая')
        self.player_count.setValue(0)
        self.rec_age.setCurrentText('Для всех возрастов')
        self.game_time.setValue(0)

    def text_format(self, text: str, j: int):  # форматирует текст и возвращает его
        """
        the function formats the text correctly for easier reading
        :param text: str
        :param j: int
        :return: str
        """
        # j - число из for
        form = {
            0: 'Название игры: ',
            1: 'Количество игроков: ',
            2: '',
            3: 'Длительность одной игры: ',
            4: ' минут.',
            5: 'Возраст игроков: ',
            6: 'Сложность игры: ',
            7: 'Краткое описание:\n'
        }
        generated = ''
        if j != 4:
            generated += form[j]
        if j in (1, 3):
            gener = f'{text[j]}-'
        elif j == 5:
            gener = f'{str(text[j])}+'
        elif j == 6:
            gener = db.cur.execute(f'select difficulty from difficulties'
                                   f' where ind = "{text[j]}"').fetchall()[0][0]
        elif j == 4:
            gener = str(text[j]) + form[j]
        else:
            gener = str(text[j])
            gener += '\n' if j not in (1, 3) else ''
        if j in (4, 5, 6):
            gener += '\n'
        generated += gener
        return generated

    def plain_text(self, text):
        """
        the function sets the text in the output field
        :param text: str
        :return: None
        """
        extensions = {  # расширения картинок
            1: 'jpg',
            2: 'png'
        }
        layout = QGridLayout()
        self.buttons_group = QButtonGroup()  # отчищаем кнопки
        generated = ''
        for i in text:
            for j in range(8):
                generated += self.text_format(i, j)
            if generated != '':
                try:  # обходит ошибку на случай если изображения нет
                    pixmap = QPixmap(f'images/{i[0]}.{extensions[i[-2]]}')
                    picture = QLabel(self)
                    picture.setPixmap(pixmap)
                    picture.setMaximumSize(720, 600)
                    layout.addWidget(picture)
                finally:
                    label = QLabel(generated)
                    label.setWordWrap(True)  # авто перенос слов на другую строку
                    layout.addWidget(label)
                    button = QPushButton(self.get_button_name_to_set(i[0], not i[-1]))  # делаем кнопку
                    # not потому что нужно противоположное значение для правильного текста на кнопке
                    self.buttons_group.addButton(button)  # добавляем кнопку в группу кнопок
                    layout.addWidget(button)  # добавляем кнопку на QScrollArea
                    layout.addWidget(QLabel('\n\n'))  # разделитель между двумя играми
                    widget = QWidget()
                    widget.setLayout(layout)
                    self.scrollArea.setWidget(widget)  # устанавливаем виджет на QScrollArea
            generated = ''
            self.buttons_group.buttonClicked.connect(self.add_to_favorites)

        if not self.not_statusbar:
            self.statusbar_print(round(time.time() - self.timer, 2))
            # устанавливает за сколько времени был выполнен поиск в статусбар
        self.print_timer(round(time.time() - self.timer, 2), 'Вывод')

    def name_in_str(self, string):  # возвращает название игры с кнопки
        """
        the function returns the name of the game from the button
        :param string: str
        :return: str
        """
        return ' '.join(string.split()[1:-2])

    def add_to_favorites(self, button):  # добавляет в избранное
        """
        the function adds the game to favorites
        :param button: QBushButton
        :return: None
        """
        name = self.name_in_str(button.text())
        is_favorite = db.get_favorite(name)[0][0]  # геттер из бд возвращает 1 или 0 есть ли в избранном
        db.set_favorite(name, is_favorite)  # добавляет в избранное
        button.setText(self.get_button_name_to_set(name, is_favorite))  # меняем название кнопки
        self.buttons_group.buttonClicked.disconnect()
        self.buttons_group.buttonClicked.connect(self.add_to_favorites)
        # 346-347. отключаем и подключаем группу кнопок к функции чтобы она не вызвалась повторно
        self.find_games()  # заново выполняем поиск, чтобы показать изменения

    def get_button_name_to_set(self, name, is_favorite):  # функция возвращает строку которая, устанавливается на кнопку
        """
        the function returns a string that is set to the button
        :param name: str
        :param is_favorite: int
        :return: str
        """
        return f'Удалить {name} из избранного' if not is_favorite else f'Добавить {name} в избранное'

    def statusbar_print(self, timer):
        """
        the function sets the value in the statusbar
        :param timer: int
        :return: None
        """
        self.statusbar.showMessage(f'Поиск успешно выполнен за {timer} секунд.')

    def print_timer(self, timer, action, nothing_found=False):
        """
        the function outputs to the console the time for which the request was made
        :param nothing_found: bool
        :param action: str
        :param timer: int
        :return: None
        """
        print('Nothing found' if nothing_found else f'{action} выполнен за {timer} секунд.\n')

    def create_dialog(self, game_name):
        """
        the function creates a dialog box in which it clarifies correctly and the user has entered the name of the game
        :param game_name: str
        :return: None
        """
        msg = QMessageBox(self)
        msg.setText(f'Возможно вы имели ввиду {game_name}?')
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)  # устанавливаем кнопки в диалоговое окно
        result = msg.exec_()  # сохраняем результат

        if result == 65536:
            self.scroll_clear()  # отчищает ScrollArea
            msg = QMessageBox(self)  # уведомляет пользователя о том что ничего не найдено
            msg.setText('По Вашему запросу ничего не найдено.')
            msg.exec()
            self.not_statusbar = True
        elif result == 16384:  # исправляет неправильное название на правильное и выполняет поиск
            self.find_by_name(game_name)
            self.not_statusbar = False  # переменная для временного выключения статусбара

    def scroll_clear(self):
        """
        the function clears QScrollArea from text and images
        :return: None
        """
        label = QLabel(self)
        self.scrollArea.setWidget(label)

    def except_hook(self, exception, traceback):
        sys.__excepthook__(self, exception, traceback)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    db = DatabaseQuery()
    ex = BGFWindow()
    ex.show()
    sys.excepthook = ex.except_hook
    sys.exit(app.exec())
