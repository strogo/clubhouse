from eosclubhouse.libquest import Quest
from eosclubhouse.system import Desktop, App, Sound


class Chore(Quest):

    APP_NAME = 'com.endlessm.OperatingSystemApp'

    def __init__(self):
        super().__init__('Chore', 'saniel')
        self._app = App(self.APP_NAME)

    def step_first(self, time_in_step):
        if time_in_step == 0:
            if Desktop.app_is_running(self.APP_NAME):
                return self.step_explanation
            self.show_hints_message('LAUNCH')
            Desktop.add_app_to_grid(self.APP_NAME)
            Desktop.focus_app(self.APP_NAME)

        if Desktop.app_is_running(self.APP_NAME) or self.debug_skip():
            return self.step_end

    def step_end(self, time_in_step):
        if time_in_step == 0:
            self.conf['complete'] = True
            self.available = False
            self.show_question('END', confirm_label='Bye')
            Sound.play('quests/quest-complete')
        if self.confirmed_step():
            self.stop()

    def step_abort(self, time_in_step):
        if time_in_step == 0:
            Sound.play('quests/quest-aborted')
            self.show_message('ABORT')

        if time_in_step > 5:
            self.stop()
