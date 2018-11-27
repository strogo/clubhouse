from eosclubhouse.utils import QS
from eosclubhouse.libquest import Quest
from eosclubhouse.system import Desktop, App, Sound


class Fizzics2(Quest):

    TARGET_APP_DBUS_NAME = 'com.endlessm.Fizzics'

    def __init__(self):
        super().__init__('Fizzics 2', 'ricky', QS('FIZZICS2_QUESTION'))
        self._app = App(self.TARGET_APP_DBUS_NAME)
        self._initialized = False
        self._hintIndex = -1
        self._hints = []
        self._hint_character_id = None

    def set_hints(self, dialog_id, character_id=None):
        self._hintIndex = -1
        self._hints = [QS(dialog_id)]
        self._hint_character_id = character_id
        hintIndex = 0
        while True:
            hintIndex += 1
            hintId = dialog_id + '_HINT' + str(hintIndex)
            hintStr = QS(hintId)
            if hintStr is None:
                break
            self._hints.append(hintStr)
        self.show_next_hint()

    def show_next_hint(self):
        if self._hintIndex >= len(self._hints) - 1 or self._hintIndex < 0:
            self._hintIndex = 0
            label = "Give me a hint"
        else:
            self._hintIndex += 1
            if self._hintIndex == len(self._hints) - 1:
                label = "What's my goal?"
            else:
                label = "I'd like another hint"
        self.show_message(self._hints[self._hintIndex], choices=[(label, self.show_next_hint)],
                          character_id=self._hint_character_id)

    # STEP 0
    def step_first(self, time_in_step):
        if time_in_step == 0:
            if not Desktop.app_is_running(self.TARGET_APP_DBUS_NAME):
                self.set_hints('FIZZICS2_LAUNCH')
                Desktop.show_app_grid()
            else:
                return self.step_alreadyrunning

        if Desktop.app_is_running(self.TARGET_APP_DBUS_NAME):
            return self.step_delay1

    def step_delay1(self, time_in_step):
        if time_in_step > 2:
            return self.step_set_level

    def step_alreadyrunning(self, time_in_step):
        if time_in_step == 0:
            self.show_question(QS('FIZZICS2_ALREADY_RUNNING'))

        if self.confirmed_step():
            return self.step_set_level

    def step_set_level(self, time_in_step):
        try:
            if not self._initialized:
                self._app.set_object_property('view.JSContext.globalParameters',
                                              'preset', ('i', 11))
                self._initialized = True
        except Exception as ex:
            print(ex)

        if self._initialized:
            return self.step_goal

    def step_goal(self, time_in_step):
        if time_in_step == 0:
            self.set_hints('FIZZICS2_GOAL')

        try:
            if self._app.get_object_property('view.JSContext.globalParameters', 'quest0Success'):
                return self.step_success
        except Exception as ex:
            print(ex)
        if not Desktop.app_is_running(self.TARGET_APP_DBUS_NAME):
            return self.step_abort

    def step_success(self, time_in_step):
        if time_in_step == 0:
            self.show_question(QS('FIZZICS2_SUCCESS'))

        if self.confirmed_step():
            return self.step_reward

    def step_reward(self, time_in_step):
        if time_in_step == 0:
            self.show_question(QS('FIZZICS2_REWARD'))
        if self.confirmed_step():
            return self.step_end

    def step_end(self, time_in_step):
        if time_in_step == 0:
            self.show_question(QS('FIZZICS2_END'))
            self.conf['complete'] = True
            self.available = False
            self.give_item('item.key.hackdex1.1')
            Sound.play('quests/quest-complete')

        if self.confirmed_step():
            self.stop()

    # STEP Abort
    def step_abort(self, time_in_step):
        if time_in_step == 0:
            self.show_message(QS('FIZZICS2_ABORT'))

        if time_in_step > 5:
            self.stop()
