
from eosclubhouse.utils import QS
from eosclubhouse.libquest import Registry, QuestSet
from eosclubhouse.quests.episode2.lightspeedintro import LightSpeedIntro
from eosclubhouse.quests.episode2.lightspeedtweak import LightSpeedTweak
from eosclubhouse.quests.episode2.lightspeedenemya1 import LightSpeedEnemyA1
from eosclubhouse.quests.episode2.lightspeedenemya2 import LightSpeedEnemyA2
from eosclubhouse.quests.episode2.lightspeedenemya3 import LightSpeedEnemyA3
from eosclubhouse.quests.episode2.lightspeedenemya4 import LightSpeedEnemyA4
from eosclubhouse.quests.episode2.powerups1 import PowerUps1
from eosclubhouse.quests.episode2.powerups2 import PowerUps2


class AdaQuestSet(QuestSet):

    __character_id__ = 'ada'
    __position__ = (38, 206)
    __quests__ = [LightSpeedIntro, LightSpeedTweak, LightSpeedEnemyA1, LightSpeedEnemyA2,
                  LightSpeedEnemyA3, LightSpeedEnemyA4, PowerUps1, PowerUps2]

    def get_empty_message(self):
        if Registry.get_quest_set_by_name('RileyQuestSet').is_active():
            return QS('NOQUEST_ADA_RILEY')
        if Registry.get_quest_set_by_name('SanielQuestSet').is_active():
            return QS('NOQUEST_ADA_SANIEL')
        if Registry.get_quest_set_by_name('FaberQuestSet').is_active():
            return QS('NOQUEST_ADA_FABER')

        return QS('NOQUEST_ADA_NOTHING')


Registry.register_quest_set(AdaQuestSet)