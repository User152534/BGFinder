import sys
import io
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QGridLayout, QPushButton, QWidget, QScrollArea,\
    QLabel
from PyQt5.QtGui import QPixmap
from PyQt5 import uic
import sqlite3
import time


class EmptySqlResult(Exception):
    def __init__(self, string):
        if not string:
            self.__str__()

    def __str__(self):
        return 'ERROR: Nothing found'


class WrongName(Exception):
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
            ex.create_dialog(", ".join(possible_names))

        """ex.textBrowser.setText('')
        ex.textBrowser.setText(f'Возможно вы имели ввиду {", ".join(possible_names)}?')"""


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
        game_diff, player_count, rec_age, game_time, game_name = values

        dif_str = self.difficulty_sql_generate(game_diff)
        pl_str = self.players_sql_generate(dif_str, player_count)
        age_str = self.age_sql_generate(dif_str, pl_str, rec_age)
        tm_str = self.time_sql_generate(dif_str, pl_str, age_str, game_time)
        nm_str = self.name_sql_generate(dif_str, pl_str, age_str, tm_str, game_name)

        self.print_sql_to_console(f'''select * from data
                  {('where ' if dif_str + pl_str + age_str + tm_str + nm_str else '') + dif_str + pl_str
                   + age_str + tm_str + nm_str}\n''')

        result = self.cur.execute(f'''select * from data
                                      {('where ' if dif_str + pl_str + age_str + tm_str + nm_str else '') + dif_str +
                                       pl_str + age_str + tm_str + nm_str}''').fetchall()
        try:
            if game_name != '':
                raise WrongName(game_name)
        except WrongName:
            print('Wrong game name')
        try:
            if not result:
                raise EmptySqlResult(result)
        except EmptySqlResult:
            print('Nothing found')
        return result

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
        if player_count != 'Любое':
            return f'{"" if not difficulty else "and "}players = "{player_count}" '
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
            return f'{"" if not difficulty and not player_count else "and "}age = "{rec_age}" '
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
        if game_time != 'Неограниченно':
            return f'{"" if not difficulty and not player_count and not rec_age else "and "}time = "{game_time}" '
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


class BGFWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        f = io.StringIO(open('BGFinder_design_testing.ui', encoding='utf8').read())
        uic.loadUi(f, self)
        for i in db.cur.execute('''select distinct age from data''').fetchall():
            self.rec_age.addItem(i[0])
        for i in db.cur.execute('''select distinct players from data''').fetchall():
            self.player_count.addItem(i[0])
        for i in db.cur.execute('''select distinct time from data''').fetchall():
            self.game_time.addItem(i[0])

        self.timer = 0
        self.statusBar()
        self.init_ui()

    def init_ui(self):
        """
        the function sets the name of the window and fixes its size
        :return: None
        """
        self.setWindowTitle('BGFinder0.0.5')
        self.setFixedSize(800, 600)
        self.find_button.clicked.connect(self.find_games)

    def find_games(self):
        """
        the function executes a search query and passes the data to the function for output
        :return: None
        """
        self.timer = time.time()
        self.print_timer(f'Поиск выполнен за {round(time.time() - self.timer, 2)} секунд.\n')
        self.plain_text(db.query_generator(self.game_diff.currentText(), self.player_count.currentText(),
                                           self.rec_age.currentText(), self.game_time.currentText(),
                                           self.game_name.text().capitalize()))

    def find_by_name(self, name):
        """
        the function changes the name of the game with an error to search ONLY BY NAME
        :param name: str
        :return: None
        """
        self.game_name.setText(name)
        self.find_games()

    def plain_text(self, text):
        """
        the function sets the text in the output field
        :param text: str
        :return: None
        """
        form = {
            0: 'Название игры: ',
            1: 'Количество игроков: ',
            2: 'Длительность одной игры: ',
            3: 'Возраст игроков: ',
            4: 'Сложность игры: ',
            5: 'Краткое описание:\n'
        }
        layout = QGridLayout()
        generated = ''
        for i in text:
            for j in range(6):
                generated = (generated + form[j] +
                             (i[j] if j != 4 else db.cur.execute(f'select difficulty from difficulties'
                                                                 f' where ind = "{i[j]}"').fetchall()[0][0])
                             + '\n' + ('\n' if j == 5 else ''))
            if generated != '':
                try:
                    pixmap = QPixmap(f'{i[0]}.jpg')
                    picture = QLabel(self)
                    picture.setPixmap(pixmap)
                    picture.setMaximumSize(720, 600)
                    layout.addWidget(picture)
                except:
                    pass
                label = QLabel(generated)
                label.setWordWrap(True)
                layout.addWidget(label)
                widget = QWidget()
                widget.setLayout(layout)
                self.scrollArea.setWidget(widget)
            generated = ''
        self.statusbar.showMessage(f'Поиск успешно выполнен за {round(time.time() - self.timer, 2)} секунд.')
        self.print_timer(f'Вывод успешно выполнен за {round(time.time() - self.timer, 2)} секунд.')

    def print_timer(self, timer):
        """
        the function outputs to the console the time for which the request was made
        :param timer: str
        :return: None
        """
        print(timer)

    def create_dialog(self, game_name):
        """
        the function creates a dialog box in which it clarifies correctly and the user has entered the name of the game
        :param game_name: str
        :return: None
        """
        msg = QMessageBox(self)
        msg.setText(f'Возможно вы имели ввиду {game_name}?')
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        result = msg.exec_()
        if result == 65536:
            self.textBrowser.setText('По вашему запросу ничего не найдено.')
        elif result == 16384:
            self.game_name.setText(game_name)
            self.find_by_name(game_name)

    def except_hook(self, exception, traceback):
        sys.__excepthook__(self, exception, traceback)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    db = DatabaseQuery()
    ex = BGFWindow()
    ex.show()
    sys.excepthook = ex.except_hook
    sys.exit(app.exec())

"""
идеи:
1. сделать поиск похожих по названию (если пользователь ошибся в названии)                ✓
2. Написать свои ошибки для разных ситуаций (ошибка при выводе и тд.)                     ✓
3. Разделить функцию query_generator класса DatabaseQuery на несколько маленьких          ✓
4. Написать doc-string к каждой функции                                                   ✓
5. Заменить текстовый виджет на QScrollArea                                               ✓
6. Добавить возможность добавлять игры в избранное                                        -
7. Расширь базу данных                                                                    ~
8. Добавь изображение к каждой игре                                                       ~
"""
