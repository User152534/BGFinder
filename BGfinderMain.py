import sys
import io
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
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
        self.possible_results()

    def __str__(self):
        return 'ERROR: Wrong name'

    def possible_results(self):
        possible_names = list()
        for name in self.names:
            possible_set = set(name[0] + self.name)
            s = 0
            for i in possible_set:
                if i in name[0] and i in self.name:
                    s += 1
            if s / len(possible_set) * 100 > 50 or name[0] in self.name:
                possible_names.append(name[0])
        print(f'Возможно вы имели ввиду {", ".join(possible_names)}?')
        ex.textBrowser.setText('')
        ex.textBrowser.setText(f'Возможно вы имели ввиду {", ".join(possible_names)}?')


class DatabaseQuery:
    def __init__(self):
        self.con = sqlite3.connect('mybase.db')
        self.cur = self.con.cursor()

    def query_generator(self, *values):
        """
        the function ...
        :param values:
        :return:
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
        print(sql)

    def difficulty_sql_generate(self, difficulty):
        """
        the function ...
        :param difficulty:
        :return: str
        """
        if difficulty != 'Любая':
            return f'''difficulty = (select ind from difficulties
            where difficulty = "{difficulty}") '''
        return ''

    def players_sql_generate(self, difficulty, player_count):
        """
        the function ...
        :param difficulty:
        :param player_count:
        :return: str
        """
        if player_count != 'Любое':
            return f'{"" if not difficulty else "and "}players = "{player_count}" '
        return ''

    def age_sql_generate(self, difficulty, player_count, rec_age):
        """
        the function ...
        :param difficulty:
        :param player_count:
        :param rec_age:
        :return: str
        """
        if rec_age != 'Для всех возрастов':
            return f'{"" if not difficulty and not player_count else "and "}age = "{rec_age}" '
        return ''

    def time_sql_generate(self, difficulty, player_count, rec_age, game_time):
        """
        the function ...
        :param difficulty:
        :param player_count:
        :param rec_age:
        :param game_time:
        :return: str
        """
        if game_time != 'Неограниченно':
            return f'{"" if not difficulty and not player_count and not rec_age else "and "}time = "{game_time}" '
        return ''

    def name_sql_generate(self, difficulty, player_count, rec_age, game_time, game_name):
        """
        the function ...
        :param difficulty:
        :param player_count:
        :param rec_age:
        :param game_time:
        :param game_name:
        :return: str
        """
        if game_name != '':
            condition = "" if not difficulty and not player_count and not rec_age and not game_time else "and "
            return f'{condition}name = "{game_name}"'
        return ''


class BGFWindow(QMainWindow):
    def __init__(self):
        """
        the function initializes the class with the application window
        """
        super().__init__()
        f = io.StringIO(open('BGFinder_design0.0.4.ui', encoding='utf8').read())
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
        self.setWindowTitle('BGFinder0.0.3')
        self.setFixedSize(630, 480)
        self.find_button.clicked.connect(self.find_games)

    def find_games(self):
        """
        the function executes a search query and passes the data to the function for output
        :return: None
        """
        self.timer = time.time()
        self.textBrowser.clear()
        self.print_timer(f'Поиск выполнен за {round(time.time() - self.timer, 2)} секунд.\n')
        self.plain_text(db.query_generator(self.game_diff.currentText(), self.player_count.currentText(),
                                           self.rec_age.currentText(), self.game_time.currentText(),
                                           self.game_name.text().capitalize()))

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
        for i in text:
            for j in range(6):
                self.textBrowser.setText(self.textBrowser.toPlainText() + form[j] +
                                         (i[j] if j != 4 else db.cur.execute(f'select difficulty from difficulties'
                                                                             f' where ind = "{i[j]}"').fetchall()[0][
                                             0])
                                         + '\n' + ('\n' if j == 5 else ''))
        self.statusbar.showMessage(f'Поиск успешно выполнен за {round(time.time() - self.timer, 2)} секунд.')
        self.print_timer(f'Вывод успешно выполнен за {round(time.time() - self.timer, 2)} секунд.')

    def print_timer(self, string):
        print(string)

    """def finder(self, query):
        return db.cur.execute(query).fetchall()[0][0]
        """

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
1. сделать поиск похожих по названию (если пользователь ошибся в названии)                -
2. Написать свои ошибки для разных ситуаций (ошибка при выводе и тд.)                     ✓
3. Разделить функцию query_generator класса DatabaseQuery на несколько маленьких          ✓
4. Написать doc-string к каждой функции                                                   ~
"""
