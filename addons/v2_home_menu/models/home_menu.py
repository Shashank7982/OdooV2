# -*- coding: utf-8 -*-
from odoo import models, api


class HomeMenuController(models.AbstractModel):
    _name = 'v2.home.menu'
    _description = 'V2 Home Menu Data Provider'

    @api.model
    def get_apps(self):
        """Return all visible top-level app menus for the current user."""
        menus = self.env['ir.ui.menu'].with_context(ir_ui_menu_full_list=False)
        root = menus.search([('parent_id', '=', False)])
        result = []
        for app in root:
            if not app.action:
                continue
            item = {
                'id': app.id,
                'name': app.name,
                'xmlid': app.complete_name,
                'action': app.action.id if app.action else False,
                'web_icon': app.web_icon or '',
                'web_icon_data': app.web_icon_data.decode('utf-8') if app.web_icon_data else '',
            }
            result.append(item)
        return result
