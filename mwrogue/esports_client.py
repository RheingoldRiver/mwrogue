import copy
import json
import re

import mwparserfromhell
from mwclient.page import Page
from typing import List, Union, Optional, Literal

from mwparserfromhell.nodes.extras import Parameter

from .auth_credentials import AuthCredentials
from mwcleric.clients.cargo_client import CargoClient

from .error_reporting.wiki_content_error import WikiContentError
from .error_reporting.wiki_script_error import WikiScriptError
from .errors import CantFindMatchHistory
from .lookup_cache import EsportsLookupCache
from mwcleric.fandom_client import FandomClient
from mwcleric.clients.site import Site
from mwparserfromhell.nodes.template import Template

ALL_ESPORTS_WIKIS = ['lol', 'halo', 'smite', 'vg', 'rl', 'pubg', 'fortnite',
                     'apexlegends', 'fifa', 'gears', 'nba2k', 'paladins', 'siege',
                     'splatoon2', 'legendsofruneterra',
                     'default-loadout', 'commons', 'teamfighttactics', 'valorant']


class EsportsClient(FandomClient):
    """
    Functions for connecting to and editing specifically to Gamepedia esports wikis.

    If not using an esports wiki, please use GamepediaSite instead.
    """
    ALL_ESPORTS_WIKIS = ALL_ESPORTS_WIKIS
    cargo_client: CargoClient = None
    client: Site = None
    wiki: str = None

    def __init__(self, wiki: str, client: Site = None,
                 credentials: AuthCredentials = None,
                 cache: EsportsLookupCache = None,
                 lang: str = None,
                 **kwargs):
        """
        Create a site object.

        :param wiki: Name of a wiki
        :param client: WikiClient object. If this is provided, SessionManager will not be used.
        :param credentials: Optional. Provide if you want a logged-in session.
        :param stg: if it's a staging wiki or not
        """
        self.wiki = self.get_wiki(wiki)

        super().__init__(wiki, credentials=credentials, lang=lang, client=client, **kwargs)
        if cache:
            self.cache = cache
        else:
            self.cache = EsportsLookupCache(self.client, cargo_client=self.cargo_client)
        self.errors = []

    @staticmethod
    def get_wiki(wiki):
        if wiki in ['lol', 'teamfighttactics'] or wiki not in ALL_ESPORTS_WIKIS:
            return wiki
        return wiki + '-esports'

    def setup_tables(self, tables):
        if isinstance(tables, str):
            tables = [tables]
        summary = "Setting up Cargo declaration"
        for table in tables:
            tl_page = self.client.pages['Template:{}/CargoDec'.format(table)]
            doc_page = self.client.pages['Template:{}/CargoDec/doc'.format(table)]
            self.save(
                tl_page,
                '{{Declare|doc={{{1|}}}}}<noinclude>{{documentation}}</noinclude>',
                summary=summary
            )
            self.save(doc_page, '{{Cargodoc}}', summary=summary)
            tl_page.touch()
        self.create_tables(tables)
        for table in tables:
            self.client.pages['Template:{}/CargoDec'.format(table)].touch()

    def create_tables(self, tables):
        self.recreate_tables(tables, replacement=False)

    def recreate_tables(self, tables, replacement=True):
        if isinstance(tables, str):
            tables = [tables]
        templates = ['{}/CargoDec'.format(_) for _ in tables]
        self.cargo_client.recreate(templates, replacement=replacement)

    def get_one_data_page(self, event, i):
        """
        Find one data page for an event

        :param event: Overview Page of an event
        :param i: the ith page to return
        :return: a Page object of a single data page
        """
        if i == 1:
            return self.client.pages['Data:' + event]
        return self.client.pages['Data:{}/{}'.format(event, str(i))]

    def data_pages(self, event):
        """
        Find all the data pages for an event.

        :param event: Overview Page of event
        :return: generator of data pages
        """
        event = self.cache.get_target(event)
        i = 1
        data_page = self.get_one_data_page(event, i)
        while data_page.exists:
            yield data_page
            i += 1
            data_page = self.get_one_data_page(event, i)

    def query_riot_mh(self, riot_mh):
        match = re.search(r'match-details/(.+?)(&tab=.*)?$', riot_mh)
        if match[1] is None:
            raise CantFindMatchHistory
        to_search = '%{}%'.format(match[1])
        result = self.cargo_client.query(
            tables="MatchScheduleGame=MSG, Tournaments=T, MatchSchedule=MS",
            join_on="MSG.OverviewPage=T.OverviewPage, MSG.MatchId=MS.MatchId",
            fields="T.StandardName=Event, MSG.Blue=Blue, MSG.Red=Red, MS.Patch=Patch",
            where="MSG.MatchHistory LIKE\"{}\"".format(to_search)
        )
        if len(result) == 0:
            raise CantFindMatchHistory
        return result[0]

    def query_bayes_id(self, idx):
        result = self.cargo_client.query(
            tables="MatchScheduleGame=MSG, Tournaments=T, MatchSchedule=MS",
            join_on="MSG.OverviewPage=T.OverviewPage, MSG.MatchId=MS.MatchId",
            fields="MS.Patch=Patch, T.StandardName=Event",
            where="MSG.RiotPlatformGameId=\"{}\"".format(idx)
        )
        if len(result) == 0:
            raise CantFindMatchHistory
        return result[0]

    def query_qq_mh(self, qq_id):
        result = self.cargo_client.query(
            tables="MatchSchedule=MS, Tournaments=T",
            join_on="MS.OverviewPage=T.OverviewPage",
            fields="MS.Patch=Patch, T.StandardName=Event",
            where="MS.QQ=\"{}\"".format(qq_id)
        )
        if len(result) == 0:
            raise CantFindMatchHistory
        return result[0]

    def query_wp_mh(self, wp_id):
        result = self.cargo_client.query(
            tables="MatchSchedule=MS, Tournaments=T",
            join_on="MS.OverviewPage=T.OverviewPage",
            fields="MS.Patch=Patch, T.StandardName=Event",
            where="MS.WanplusId=\"{}\"".format(wp_id)
        )
        if len(result) == 0:
            raise CantFindMatchHistory
        return result[0]

    def get_data_and_timeline_from_gameid(self, game_id: str):
        """
        Queries Leaguepedia to return two jsons: The data & timeline from a single game.

        :param game_id: The Leaguepedia game_id
        :return: Two jsons, the data & timeline for the game
        """
        result = self.cargo_client.query(
            tables=["MatchScheduleGame=MSG", "PostgameJsonMetadata=PJM"],
            join_on='MSG.RiotPlatformGameId=PJM.RiotPlatformGameId',
            fields=['PJM.RiotVersion=Version', 'PJM.RiotPlatformGameId=RPGId'],
            where=f"MSG.GameId=\"{game_id}\"",
        )
        if not result:
            raise KeyError
        game = result[0]
        return self.get_data_and_timeline(rpgid=game['RPGId'], version=game['Version'])

    def get_data_and_timeline(self, rpgid: str, version: Literal[4, 5] = 4):
        """
        Queries Leaguepedia to return two jsons: The data & timeline from a single game.

        This function is limited in scope: It will not allow you to query multiple games in a single query;
        however, the MediaWiki API does support this. It also will not allow you to drop one of the jsons
        for a smaller response package if you don't require all of the data. You also must know the ID in advance.
        You can find IDs by querying the MatchScheduleGame Cargo table and looking up the RiotPlatformGameId field.

        Raises a KeyError in the case that data is not found.
        If Timeline is not found, `None` will be returned for that json (this happens for chronobreaks).

        This function is unavailable on wikis other than Leaguepedia.

        :param rpgid: A single riot_platform_game_id
        :param version: The API version of the json to download. Defaults to 4.
        :return: Two jsons, the data & timeline for the game
        """
        titles = f"V{version} data:{rpgid}|V{version} data:{rpgid}/Timeline"
        result = self.client.post(
            'query', prop='revisions', titles=titles, rvprop='content',
            rvslots='main'
        )
        data = None
        timeline = None
        for _, page_data in result['query']['pages'].items():
            # This is lazy but there's 2 pages total so it's safe tbh
            if 'Timeline' in page_data['title']:
                timeline = json.loads(page_data['revisions'][0]['slots']['main']['*'])
            else:
                data = json.loads(page_data['revisions'][0]['slots']['main']['*'])

        if data is None:
            raise KeyError
        return data, timeline

    def backup_template(self, template: Template, page: Union[str, Page],
                        key: Union[str, List[str]]):
        """
        Backs up a template in the `Backup` namespace. The template can later be restored with `get_restored_template`.

        :param template: Template object
        :param page: Page or title where the template is located on
        :param key: Identifying set of params that we can use to locate the template when we restore it
        :return: null
        """
        if isinstance(page, str):
            page = self.client.pages[page]
        if isinstance(key, str):
            key = [key]
        key_template = Template('BackupKey')
        for key_param in key:
            key_template.add(key_param, template.get(key_param, Parameter('', '')).value)

        # this method will be used in TemplateModifier so it is essential that
        # we do not modify the original
        copy_template = copy.deepcopy(template)
        copy_template.add('backup_key', str(key_template))
        self.client.pages['Backup:' + page.name].append('\n' + str(copy_template), contentmodel='text')

    def get_restored_template(self, template: Template, page: Union[str, Page],
                              key: Union[str, List[str]]) -> Optional[Template]:
        """
        Looks for the backed-up version of the specified template on the backup page & returns it

        The template should have been backed up using the backup_template method earlier.

        :param template: Template object that we want to restore from backup page
        :param page: Page or title where the template is located on
        :param key: Identifying set of params to use to restore the template from
        :return: Template object, if found, else None
        """
        if isinstance(page, str):
            page = self.client.pages[page]
        if isinstance(key, str):
            key = [key]
        backup_text = self.client.pages['Backup:' + page.name].text()
        for backup_template in mwparserfromhell.parse(backup_text).filter_templates():
            if not backup_template.name.matches(template.name):
                continue

            # kinda need to do a hack to get this as a template
            backup_key_str = str(backup_template.get('backup_key').value)
            backup_key_wikitext = mwparserfromhell.parse(backup_key_str)
            backup_key = None
            for tl in backup_key_wikitext.filter_templates():
                if tl.name.matches('BackupKey'):
                    backup_key = tl
                    break
            # now backup_key is a template value of BackupKey

            is_match = True
            i = 0
            for param in backup_key.params:
                name = param.name.strip()
                if name in key:
                    if param.value.strip() == template.get(name, Parameter('', '')).value.strip():
                        i += 1
                else:
                    is_match = False
            if i == len(key) and is_match:
                return backup_template
        return None

    def log_error_script(self, title: str = None, error: Exception = None):
        self.errors.append(WikiScriptError(title, error))

    def log_error_content(self, title: str = None, text: str = None):
        self.errors.append(WikiContentError(title, error=text))

    def report_all_errors(self, error_title):
        if not self.errors:
            return
        error_page = self.client.pages['Log:' + error_title]
        errors = [_.format_for_print() for _ in self.errors]
        error_text = '<br>\n'.join(errors)
        old_text = error_page.text(cache=False)
        if not old_text:
            new_text = error_text
        else:
            new_text = f"{old_text}<br>{error_text}"
        self.save(error_page, new_text, summary="Reporting errors via mwrogue")

        # reset the list so we can reuse later if needed
        self.errors = []

    def tournaments_to_skip(self, script):
        result = self.cargo_client.query(
            tables="TournamentScriptsToSkip",
            fields="OverviewPage",
            where=f'Script="{script}"'
        )
        tournaments_to_skip = []
        for item in result:
            tournaments_to_skip.append(item["OverviewPage"])
        return tournaments_to_skip

    def tournaments_to_skip_where(self, script, field):
        tournaments_to_skip = self.tournaments_to_skip(script)
        condition = ','.join(['"{}"'.format(_) for _ in tournaments_to_skip])
        return f"{field} NOT IN ({condition})"
