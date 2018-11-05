from eosclubhouse.utils import QS
from eosclubhouse.libquest import Quest
from eosclubhouse.system import Desktop, App


class Fizzics1(Quest):

    TARGET_APP_DBUS_NAME = 'com.endlessm.Fizzics'

    def __init__(self):
        super().__init__('Fizzics 1', 'ricky', QS('FIZZICS1_QUESTION'))
        self._app = App(self.TARGET_APP_DBUS_NAME)
        self._hint0 = False
        self._hint1 = False
        self._hintCount = False
        self._initialized = False
        self._msg = ""
        self.gss.connect('changed', self.update_availability)
        self.available = False
        self.update_availability()

    def update_availability(self, gss=None):
        if self.conf['complete']:
            return
        if self.is_named_quest_complete("FizzicsIntro"):
            self.available = True

    # STEP 0
    def step_first(self, time_in_step):
        if time_in_step == 0:
            self.show_message(QS('FIZZICS1_LAUNCH'))

        if Desktop.app_is_running(self.TARGET_APP_DBUS_NAME) or self.debug_skip():
            return self.step_goal

        if time_in_step > 20 and not self._hint0:
            self.show_message(QS('FIZZICS1_LAUNCHHINT'))
            self._hint0 = True

    # STEP 1
    def step_goal(self, time_in_step):
        if time_in_step == 0:
            self.show_message(QS('FIZZICS1_GOAL'))

        if time_in_step < 3:
            return

        try:
            if not self._initialized:
                self._app.set_object_property('view.JSContext.globalParameters',
                                              'preset', ('i', 11))
                self._initialized = True
        except Exception as ex:
            print(ex)

        if time_in_step > 20:
            return self.step_wait_score

    def step_wait_score(self, time_in_step):
        if time_in_step == 0:
            self._msg = QS('FIZZICS1_EXPLANATION')
            self.show_message(self._msg)
            self.give_item('item.key.fizzics.1')

        try:
            if self._app.get_object_property('view.JSContext.globalParameters',
                                             'quest0Success'):
                return self.step_success

            type1BallCount = self._app.get_object_property('view.JSContext.globalParameters',
                                                           'type1BallCount')
            if time_in_step > 5 and type1BallCount < 20 and not self._hintCount:
                self.show_message(QS('FIZZICS1_NOTENOUGH'))
                self._hintCount = True
            elif type1BallCount >= 20 and self._hintCount:
                self.show_message(self._msg)
                self._hintCount = False
            elif time_in_step > 60 and not self._hint1:
                self._msg = QS('FIZZICS1_HINT')
                self.show_message(self._msg)
                self._hint1 = True
        except Exception as ex:
            print(ex)

        if self.debug_skip():
            return self.step_success

        if not Desktop.app_is_running(self.TARGET_APP_DBUS_NAME):
            return self.step_end_no_app

    # STEP 2
    def step_success(self, time_in_step):
        if time_in_step == 0:
            self.show_question(QS('FIZZICS1_SUCCESS'))

        if self.confirmed_step():
            return self.step_prereward

    def step_prereward(self, time_in_step):
        if time_in_step == 0:
            if self.is_named_quest_complete("OSIntro"):
                msg = 'FIZZICS1_KEY_ALREADY_OS'
            else:
                msg = 'FIZZICS1_KEY_NO_OS'
            self.show_question(QS(msg))

        if self.confirmed_step():
            return self.step_reward

    # STEP 4
    def step_reward(self, time_in_step):
        if time_in_step == 0:
            self.give_item('item.key.OperatingSystemApp.1')
            self.show_question(QS('FIZZICS1_GIVE_KEY'))
            self.conf['complete'] = True
            self.available = False

        if self.confirmed_step():
            self.stop()

    # STEP Abort
    def step_end_no_app(self, time_in_step):
        if time_in_step == 0:
            self.show_message(QS('FIZZICS1_ABORT'))

        if time_in_step > 5:
            self.stop()
