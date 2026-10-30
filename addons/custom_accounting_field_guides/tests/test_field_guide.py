import base64

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountFieldGuide(TransactionCase):

    def test_all_seeded_guides_download(self):
        """ Every seeded guide must generate a valid, non-empty XLSX
        attachment, and every field it lists must exist on its target
        model - catches drift if a field is renamed/removed. """
        guides = self.env['account.field.guide'].search([])
        self.assertTrue(guides, 'Seed data should have created field guides.')
        for guide in guides:
            if guide.model_name not in self.env:
                continue  # target module not installed in this DB - skip
            action = guide.action_download()
            self.assertEqual(action['type'], 'ir.actions.act_url')
            attachment = self.env['ir.attachment'].search(
                [('name', '=', '%s_field_guide.xlsx' % (guide.key or guide.model_name.replace('.', '_')))],
                order='id desc', limit=1)
            self.assertTrue(attachment, 'Expected an xlsx attachment for %s' % guide.key)
            content = base64.b64decode(attachment.datas)
            self.assertTrue(content.startswith(b'PK'), 'Should be a real XLSX (zip) file for %s' % guide.key)

    def test_missing_field_raises(self):
        guide = self.env['account.field.guide'].create({
            'name': 'Broken Guide',
            'key': 'broken_guide_test',
            'guide_type': 'field_guide',
            'feature_group': 'other',
            'model_name': 'res.partner',
            'field_names': 'this_field_does_not_exist',
        })
        with self.assertRaises(Exception):
            guide.action_download()

    def test_unknown_model_raises(self):
        guide = self.env['account.field.guide'].create({
            'name': 'Unknown Model Guide',
            'key': 'unknown_model_guide_test',
            'guide_type': 'field_guide',
            'feature_group': 'other',
            'model_name': 'this.model.does.not.exist',
            'field_names': 'name',
        })
        with self.assertRaises(Exception):
            guide.action_download()
