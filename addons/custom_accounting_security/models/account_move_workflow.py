from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMoveWorkflow(models.Model):
    _inherit = 'account.move'

    state = fields.Selection(
        # The final ('posted',) item is an insertion anchor: it places the
        # custom approval stages before Odoo's existing Posted state.
        selection_add=[
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('posted',),
        ],
        ondelete={'submitted': 'set default', 'approved': 'set default'},
    )

    def _is_workflow_context(self):
        return self.env.context.get('accounting_workflow_transition') or self.env.context.get('skip_accounting_workflow')

    def _is_manager(self):
        return self.env.user.has_group('custom_accounting_security.group_accounting_manager')

    def _is_controller(self):
        return self.env.user.has_group('custom_accounting_security.group_accounting_finance_controller')

    def _is_user(self):
        return self.env.user.has_group('custom_accounting_security.group_accounting_user')

    def _is_cfo(self):
        return self.env.user.has_group('custom_accounting_security.group_accounting_cfo_admin')

    def _is_privileged(self):
        return self.env.su or self._is_user() or self._is_controller() or self._is_manager()

    def _is_noop_write(self, vals):
        """Recognize the unchanged write sent by the form before an action.

        Odoo saves a form before executing an object button.  A read-only
        controller can therefore receive a write containing the current
        values even though no edit was made.  Permit that harmless save, but
        never permit an actual field or journal-line change.
        """
        for field_name, value in vals.items():
            if field_name == 'line_ids':
                if not isinstance(value, (list, tuple)):
                    return False
                for command in value:
                    if not isinstance(command, (list, tuple)) or len(command) != 3 or command[0] != 1:
                        return False
                    line = self.env['account.move.line'].browse(command[1])
                    if not line or line.move_id not in self:
                        return False
                    for line_field, line_value in command[2].items():
                        field = line._fields.get(line_field)
                        if not field or field.type in ('one2many', 'many2many'):
                            return False
                        current = field.convert_to_cache(line[line_field], line)
                        incoming = field.convert_to_cache(line_value, line)
                        if field.type == 'many2one':
                            current = current.id if current else False
                            incoming = incoming.id if incoming else False
                        if current != incoming:
                            return False
                continue
            field = self._fields.get(field_name)
            if not field or len(self) != 1 or field.type in ('one2many', 'many2many'):
                return False
            current = field.convert_to_cache(self[field_name], self)
            incoming = field.convert_to_cache(value, self)
            if field.type == 'many2one':
                current = current.id if current else False
                incoming = incoming.id if incoming else False
            if current != incoming:
                return False
        return True

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.su is not True and not self._is_user():
            raise UserError(_('Only an Accounting User can create accounting entries.'))
        if any(vals.get('state') not in (None, 'draft') for vals in vals_list):
            raise UserError(_('New accounting entries must start in Draft.'))
        # Odoo performs protected computed-field writes while constructing the
        # move; those internal writes must not be mistaken for user edits.
        created = super(AccountMoveWorkflow, self.with_context(skip_accounting_workflow=True)).create(vals_list)
        return created.with_env(self.env)

    def write(self, vals):
        if not vals:
            return True
        if 'state' in vals and not self._is_workflow_context():
            raise UserError(_('Use the workflow buttons to change an accounting entry status.'))
        if not self._is_workflow_context():
            # Odoo may flush stored computed fields (for example sequence
            # metadata) immediately before an object button is executed.
            # These are framework writes, not Finance Controller edits.
            if (self._is_controller() or self._is_cfo()) and all(
                self._fields.get(name) and self._fields[name].compute and self._fields[name].store
                for name in vals
            ):
                return super().write(vals)
            if self._is_cfo() or not self._is_user():
                # Object buttons auto-save the form first.  Controllers and
                # managers are read-only, but that save is harmless when it
                # contains exactly the values already on the record.  It
                # must be allowed in every workflow state used by their
                # respective buttons, including Approved -> Posted.
                if (
                    (self._is_controller() and all(move.state == 'draft' for move in self))
                    or self._is_manager()
                    or self._is_cfo()
                ) and self._is_noop_write(vals):
                    return super().write(vals)
                raise UserError(_('This role has read-only access to accounting entries.'))
            if any(move.state != 'draft' for move in self):
                raise UserError(_('Only Draft accounting entries can be edited.'))
        return super().write(vals)

    def action_submit(self):
        if not self._is_controller():
            raise UserError(_('Only a Finance Controller can submit a Draft entry.'))
        if any(move.state != 'draft' for move in self):
            raise UserError(_('Only Draft entries can be submitted.'))
        self.with_context(accounting_workflow_transition=True).write({'state': 'submitted'})
        return True

    def action_approve(self):
        if not self._is_manager():
            raise UserError(_('Only an Accounting Manager can approve an entry.'))
        if any(move.state != 'submitted' for move in self):
            raise UserError(_('Only Submitted entries can be approved.'))
        self.with_context(accounting_workflow_transition=True).write({'state': 'approved'})
        return True

    def action_post(self):
        if self.env.context.get('skip_accounting_workflow'):
            return super().action_post()
        if not self._is_manager():
            raise UserError(_('Only an Accounting Manager can post an entry.'))
        if any(move.state != 'approved' for move in self):
            raise UserError(_('Only Approved entries can be posted.'))
        return super(AccountMoveWorkflow, self.with_context(accounting_workflow_transition=True)).action_post()

    def button_cancel(self):
        """Allow the creator to cancel an unsubmitted Draft entry.

        The standard Odoo button writes ``state = cancel`` directly.  Our
        workflow guard intentionally blocks direct state writes, so the
        standard cancellation must pass through the guarded transition
        context.  Submitted, approved, and posted entries still cannot be
        cancelled through this action.
        """
        if not self._is_user():
            raise UserError(_('Only an Accounting User can cancel a Draft entry.'))
        if any(move.state != 'draft' for move in self):
            raise UserError(_('Only Draft entries can be cancelled.'))
        return super(AccountMoveWorkflow, self.with_context(
            accounting_workflow_transition=True,
        )).button_cancel()
