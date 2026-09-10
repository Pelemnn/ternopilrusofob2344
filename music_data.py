"""
Колекція з 30 культових українських повстанських (УПА), стрілецьких та козацьких патріотичних пісень
з прямими посиланнями на MP4 відео/аудіо треки.
"""

import random
from typing import Dict, Any, List

# Список з 30 пісень із прямими MP4 джерелами та текстом
UPA_SONGS: List[Dict[str, Any]] = [
    {
        "title": "Ой у лузі червона калина",
        "author": "Гімн Січових Стрільців та УПА (Степан Чарнецький)",
        "chorus": "«А ми тую червону калину підіймемо,\nА ми нашу славну Україну, гей, гей, розвеселимо!»",
        "mp4_url": "https://archive.org/download/chervona-kalyna-ukraine/chervona_kalyna.mp4",
        "link": "https://www.youtube.com/results?search_query=Ой+у+лузі+червона+калина"
    },
    {
        "title": "Батько наш — Бандера, Україна — мати",
        "author": "Повстанська народна пісня УПА",
        "chorus": "«Батько наш — Бандера, Україна — мати,\nМи за Україну підем воювати!»",
        "mp4_url": "https://archive.org/download/batko-nash-bandera-upa/batko_nash_bandera.mp4",
        "link": "https://www.youtube.com/results?search_query=Батько+наш+Бандера+Україна+мати"
    },
    {
        "title": "Лента за лентою",
        "author": "Микола Свистун / Тарас Чубай та «Плач Єремії»",
        "chorus": "«Лента за лентою набої подавай,\nВкраїнський повстанче, в бою не відступай!»",
        "mp4_url": "https://archive.org/download/lenta-za-lentoyu-upa/lenta_za_lentoyu.mp4",
        "link": "https://www.youtube.com/results?search_query=Лента+за+лентою"
    },
    {
        "title": "Зродились ми великої години",
        "author": "Олесь Бабій / Марш ОУН та Збройних Сил України",
        "chorus": "«Веде нас в бій борців упавших слава,\nДля нас закон найвищий — то наказ:\nСоборна українська держава —\nОдна навік, від Сяну по Кавказ!»",
        "mp4_url": "https://archive.org/download/zrodilis-my-velikoyi-godyny/marsh_oun_zsu.mp4",
        "link": "https://www.youtube.com/results?search_query=Зродились+ми+великої+години"
    },
    {
        "title": "Йшли селом партизани",
        "author": "Повстанська народна пісня УПА",
        "chorus": "«Йшли селом, йшли селом партизани,\nПокривалися листям дуби,\nІшли в бій за святу Україну,\nЗа свободу народу й права!»",
        "mp4_url": "https://archive.org/download/yshly-selom-partyzany-upa/yshly_selom_partyzany.mp4",
        "link": "https://www.youtube.com/results?search_query=Йшли+селом+партизани"
    },
    {
        "title": "Гей, гуляє полем",
        "author": "Тарас Чубай & Скрябін (Пісні УПА)",
        "chorus": "«Гей, гуляє полем військо молоде,\nТо повстанці славні ідуть за народ!»",
        "mp4_url": "https://archive.org/download/hey-hulyaie-polem-chubay/hey_hulyaie_polem.mp4",
        "link": "https://www.youtube.com/results?search_query=Гей+гуляє+полем+Чубай"
    },
    {
        "title": "Повіяв вітер степовий",
        "author": "Стрілецька пісня / Музика народна",
        "chorus": "«Повіяв вітер степовий, трава ся похилила,\nВпав у бою козак молодий, дівчина заплакала...»",
        "mp4_url": "https://archive.org/download/poviyav-viter-stepovyy/poviyav_viter_stepovyy.mp4",
        "link": "https://www.youtube.com/results?search_query=Повіяв+вітер+степовий"
    },
    {
        "title": "Як з Бережан до Кадри",
        "author": "Стрілецький марш (УСС та УПА)",
        "chorus": "«Як з Бережан до Кадри вчилися стріляти,\nЩоб за рідну землю ворога здолати!»",
        "mp4_url": "https://archive.org/download/yak-z-berejan-do-kadry/berezhany_kadra.mp4",
        "link": "https://www.youtube.com/results?search_query=Як+з+Бережан+до+Кадри"
    },
    {
        "title": "Там під львівським замком",
        "author": "Повстанська народна балада",
        "chorus": "«Там під львівським замком старий дуб стоїть,\nА під тим дубочком партизан лежить...»",
        "mp4_url": "https://archive.org/download/tam-pid-lvivskym-zamkom/tam_pid_lvivskym_zamkom.mp4",
        "link": "https://www.youtube.com/results?search_query=Там+під+львівським+замком"
    },
    {
        "title": "Ой, морозе, морозенку",
        "author": "Козацько-повстанська народна дума",
        "chorus": "«Ой, Морозе, Морозенку, ти славний козаче,\nЗа тобою, Морозенку, вся Вкраїна плаче!»",
        "mp4_url": "https://archive.org/download/oy-moroze-morozenku/oy_moroze_morozenku.mp4",
        "link": "https://www.youtube.com/results?search_query=Ой+морозе+морозенку"
    },
    {
        "title": "Чорна рілля ізорана",
        "author": "Козацька дума / Тарас Чубай",
        "chorus": "«Чорна рілля ізорана, гей, гей,\nІ кулями засіяна, білим тілом зволочена...»",
        "mp4_url": "https://archive.org/download/chorna-rillya-izorana/chorna_rillya_izorana.mp4",
        "link": "https://www.youtube.com/results?search_query=Чорна+рілля+ізорана+Чубай"
    },
    {
        "title": "Ми йдем вперед",
        "author": "Повстанський бойовий марш УПА",
        "chorus": "«Ми йдем вперед, над нами синій простір,\nІ прапор наш — святий блакитно-жовтий стяг!»",
        "mp4_url": "https://archive.org/download/my-ydem-vpered-upa/my_ydem_vpered.mp4",
        "link": "https://www.youtube.com/results?search_query=Ми+йдем+вперед+УПА"
    },
    {
        "title": "О Україно, о люба ненько",
        "author": "Микола Вороний / Гімн українських повстанців",
        "chorus": "«О Україно! О люба ненько,\nТобі вірненько присягнем!\nСерця гарячі, ідейні душі\nЗа тебе щиро віддаєм!»",
        "mp4_url": "https://archive.org/download/o-ukrayino-o-lyuba-nenko/o_ukrayino_o_lyuba_nenko.mp4",
        "link": "https://www.youtube.com/results?search_query=О+Україно+о+люба+ненько"
    },
    {
        "title": "Гей, соколи!",
        "author": "Українсько-польська козацька пісня",
        "chorus": "«Гей, гей, гей, соколи!\nОминайте гори, ліси, доли!\nДзвени, дзвени, дзвіночку,\nСтеповий жайвороночку!»",
        "mp4_url": "https://archive.org/download/hey-sokoly-ukraine/hey_sokoly.mp4",
        "link": "https://www.youtube.com/results?search_query=Гей+соколи"
    },
    {
        "title": "Браття українці",
        "author": "Гурт «Шабля» (Офіційний гімн АТО/ООС)",
        "chorus": "«Браття українці, захистимо неньку!\nНе дамо ми ворогу рідну землю й хату!»",
        "mp4_url": "https://archive.org/download/brattia-ukrayintsi-shablya/brattia_ukrayintsi.mp4",
        "link": "https://www.youtube.com/results?search_query=Шабля+Браття+українці"
    },
    {
        "title": "Гей, степами",
        "author": "Тарас Чубай (Альбом «Наші партизани»)",
        "chorus": "«Гей, степами темними, ярами зеленими,\nІдуть хлопці-партизани рядами стрункими!»",
        "mp4_url": "https://archive.org/download/hey-stepamy-chubay/hey_stepamy.mp4",
        "link": "https://www.youtube.com/results?search_query=Гей+степами+Чубай"
    },
    {
        "title": "Марширують наші добровольці",
        "author": "Стрілецький похідний марш",
        "chorus": "«Марширують наші добровольці у кривавий тан,\nВизволяти рідних братів з ворожих кайдан!»",
        "mp4_url": "https://archive.org/download/marshyruyut-nashi-dobrovoltsi/marshyruyut_dobrovoltsi.mp4",
        "link": "https://www.youtube.com/results?search_query=Марширують+наші+добровольці"
    },
    {
        "title": "Ой у полі верба",
        "author": "Повстанська народна пісня",
        "chorus": "«Ой у полі верба похилилася,\nЧом ти, моя Україно, засмутилася?»",
        "mp4_url": "https://archive.org/download/oy-u-poli-verba-upa/oy_u_poli_verba.mp4",
        "link": "https://www.youtube.com/results?search_query=Ой+у+полі+верба+УПА"
    },
    {
        "title": "Сміло, други, до бою",
        "author": "Бойова пісня ОУН-УПА",
        "chorus": "«Сміло, други, до бою за волю,\nЗа Вкраїну, за правду святу!»",
        "mp4_url": "https://archive.org/download/smilo-druhy-do-boyu/smilo_druhy_do_boyu.mp4",
        "link": "https://www.youtube.com/results?search_query=Сміло+други+до+бою+УПА"
    },
    {
        "title": "За Україну, за її волю",
        "author": "Стрілецький гімн визволення",
        "chorus": "«За Україну, за її волю,\nЗа честь, за славу, за народ!»",
        "mp4_url": "https://archive.org/download/za-ukrayinu-za-yiyi-volyu/za_ukrayinu.mp4",
        "link": "https://www.youtube.com/results?search_query=За+Україну+за+її+волю"
    },
    {
        "title": "Ой чути дзвін",
        "author": "Повстанська дума про бій",
        "chorus": "«Ой чути дзвін, чути дзвін гуде,\nТо на бій святий сотня УПА йде!»",
        "mp4_url": "https://archive.org/download/oy-chuty-dzvin-upa/oy_chuty_dzvin.mp4",
        "link": "https://www.youtube.com/results?search_query=Ой+чути+дзвін+УПА"
    },
    {
        "title": "Не пора, не пора",
        "author": "Іван Франко / Денис Січинський",
        "chorus": "«Не пора, не пора, не пора\nМоскалеві й ляхові служить!\nДовершилась проклята пора,\nНам пора для України жить!»",
        "mp4_url": "https://archive.org/download/ne-pora-ne-pora-franko/ne_pora_ne_pora.mp4",
        "link": "https://www.youtube.com/results?search_query=Не+пора+не+пора+Іван+Франко"
    },
    {
        "title": "Меч Арея",
        "author": "Василь Лютий / Гурт «Тінь Сонця»",
        "chorus": "«На порозі сидить сивий дід,\nВін кує для нащадків Меч Арея!\nІ гримить у віках заповіт:\nПеремога за синами землі цієї!»",
        "mp4_url": "https://archive.org/download/mech-areya-tin-sontsya/mech_areya.mp4",
        "link": "https://www.youtube.com/results?search_query=Тінь+Сонця+Меч+Арея"
    },
    {
        "title": "Ой на горі та й женці жнуть",
        "author": "Козацький похідний марш",
        "chorus": "«А позаду Сагайдачний,\nЩо проміняв тютюн та люльку на жінку — необачний!»",
        "mp4_url": "https://archive.org/download/oy-na-hori-ta-y-zhentsi-znhut/zhentsi_znhut.mp4",
        "link": "https://www.youtube.com/results?search_query=Ой+на+горі+та+й+женці+жнуть"
    },
    {
        "title": "Їхав козак за Дунай",
        "author": "Семен Климовський",
        "chorus": "«Їхав козак за Дунай, сказав: \"Дівчино, прощай!\nТи, конику вороненький, неси та гуляй!\"»",
        "mp4_url": "https://archive.org/download/yikhav-kozak-za-dunay/kozak_za_dunay.mp4",
        "link": "https://www.youtube.com/results?search_query=Їхав+козак+за+Дунай"
    },
    {
        "title": "Розпрягайте, хлопці, коней",
        "author": "Українська козацька пісня",
        "chorus": "«Розпрягайте, хлопці, коней та лягайте спочивать,\nА я піду в сад вишневий, в сад криниченьку копать!»",
        "mp4_url": "https://archive.org/download/rozpryahayte-khloptsi-koney/rozpryahayte_koney.mp4",
        "link": "https://www.youtube.com/results?search_query=Розпрягайте+хлопці+коней"
    },
    {
        "title": "Козак від'їжджає, дівчинонька плаче",
        "author": "Стрілецький романс",
        "chorus": "«Козак від'їжджає, дівчинонька плаче:\nКуди від'їжджаєш, козаче соколе?»",
        "mp4_url": "https://archive.org/download/kozak-vidyizhdzhaye/kozak_vidyizhdzhaye.mp4",
        "link": "https://www.youtube.com/results?search_query=Козак+від'їжджає+дівчинонька+плаче"
    },
    {
        "title": "Вільні люди",
        "author": "БЕЗ ОБМЕЖЕНЬ",
        "chorus": "«Ми — вільні люди, ми живемо на своїй землі!\nІ сонце зійде, розвіє темряву в імлі!»",
        "mp4_url": "https://archive.org/download/vilni-lyudy-bez-obmezhen/vilni_lyudy.mp4",
        "link": "https://www.youtube.com/results?search_query=Без+обмежень+Вільні+люди"
    },
    {
        "title": "Стефанія",
        "author": "Kalush Orchestra",
        "chorus": "«Стефанія мамо, мамо Стефанія,\nРозквітає поле, а вона сивіє...\nЗаспівай мені, мамо, колискову,\nХочу ще почути твоє рідне слово!»",
        "mp4_url": "https://archive.org/download/stefania-kalush-orchestra/stefania.mp4",
        "link": "https://www.youtube.com/results?search_query=Kalush+Stefania"
    },
    {
        "title": "Заповіт",
        "author": "Тарас Шевченко (Бойовий спів)",
        "chorus": "«Поховайте та вставайте, кайдани порвіте\nІ вражою злою кров'ю волю окропіте!»",
        "mp4_url": "https://archive.org/download/zapovit-shevchenko-song/zapovit.mp4",
        "link": "https://www.youtube.com/results?search_query=Заповіт+Шевченко+пісня"
    }
]


def get_random_upa_song() -> Dict[str, Any]:
    """Повертає одну з 30 українських повстанських пісень у форматі MP4."""
    return random.choice(UPA_SONGS)
