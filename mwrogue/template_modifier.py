from typing import Union, Optional

from mwcleric.template_modifier import TemplateModifierBase as MwclericTemplateModifier

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
        if self.current_page.name.startswith('Backup:'):
            return
        to_restore = self.site.get_restored_template(self.current_template, self.current_page, key)
        if to_restore is None:
            return
        to_restore.remove('backup_key')

        # restore stuff carefully, so that we can preserve whitespace as much as possible

        # first, restore all the params that are in both, while at the same time deleting stuff not in the backup
        for param in self.current_template.params:
            name = param.name.strip()
            if to_restore.has(name):
                self.current_template.add(name, to_restore.get(name).value.strip())
                to_restore.remove(name)
            else:
                self.current_template.remove(name)

        # now add what we missed from the to_restore template
        for param in to_restore.params:
            self.current_template.add(param.name.strip(), param.value.strip())
