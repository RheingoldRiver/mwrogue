from typing import Union, Optional

from mwcleric.template_modifier import TemplateModifierBase as MwclericTemplateModifier
from mwparserfromhell.nodes import Template

from mwrogue.esports_client import EsportsClient


class TemplateModifierBase(MwclericTemplateModifier):
    def __init__(self, site: EsportsClient, template, page_list=None, title_list=None, limit=-1, summary=None,
                 quiet=False, lag=0, tags=None, skip_pages=None,
                 recursive=True,
                 startat_page=None,
                 namespace: Optional[Union[int, str]] = None,
                 **data):
        super().__init__(site, template, page_list=page_list, title_list=title_list, limit=limit, summary=summary,
                         quiet=quiet, lag=lag, tags=tags, skip_pages=skip_pages,
                         recursive=recursive,
                         startat_page=startat_page,
                         namespace=namespace,
                         **data)

        # redo this assignment just for the type hint because it doesn't seem to get it otherwise
        self.site = site

    def backup(self, key):
        if self.current_page.name.startswith('Backup:'):
            return
        self.site.backup_template(template=self.current_template, page=self.current_page, key=key)

    def restore(self, key):
        self.current_template: Template
        if self.current_page.name.startswith('Backup:'):
            return
        to_restore = self.site.get_restored_template(self.current_template, self.current_page, key)
        if to_restore is None:
            if not self.quiet:
                if isinstance(key, str):
                    key = [key]
                print('Could not find restore data for template on page "{}" with key: {}'.format(
                    self.current_page.name,
                    ', '.join([str(self.current_template.get(_, _)) for _ in key])))
            return
        to_restore.remove('backup_key')

        for param in self.current_template.params:
            self.current_template.remove(param.name.strip())

        for param in to_restore.params:
            name = param.name.strip()
            self.current_template.add(param.name, to_restore.get(name).value, preserve_spacing=False)
