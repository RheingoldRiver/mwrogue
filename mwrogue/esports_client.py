import copy
import re

import mwparserfromhell
from mwclient.page import Page
from typing import List, Union, Optional

from mwparserfromhell.nodes.extras import Parameter

from .auth_credentials import AuthCredentials
from mwcleric.cargo_client import CargoClient
from .errors import CantFindMatchHistory
from .lookup_cache import EsportsLookupCache
from mwcleric.fandom_client import FandomClient
from mwcleric.site import Site
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
            join_on="MSG.OverviewPage=T.OverviewPage, MSG.UniqueMatch=MS.UniqueMatch",
            fields="T.StandardName=Event, MSG.Blue=Blue, MSG.Red=Red,MS.Patch=Patch",
            where="MSG.MatchHistory LIKE\"{}\"".format(to_search)
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
            if i + 1 == len(key) and is_match:
                return backup_template
        return None
