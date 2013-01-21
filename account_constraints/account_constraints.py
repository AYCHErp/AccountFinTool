# -*- coding: utf-8 -*-
##############################################################################
#
#    Author Joel Grand-Guillaume. Copyright 2012 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, orm, osv
from openerp.tools.translate import _

class AccountMove(orm.Model):
    _inherit = "account.move"

    def _check_fiscal_year(self, cr, uid, ids):
        for move in self.browse(cr, uid, ids):
            date_start = move.period_id.fiscalyear_id.date_start
            date_stop = move.period_id.fiscalyear_id.date_stop
            if not date_start <= move.date <= date_stop:
                return False
        return True

    _constraints = [
        (_check_fiscal_year,
            'You cannot create entries with date not in the '
            'fiscal year of the chosen period',
            ['line_id']),
    ]


class AccountMoveLine(orm.Model):
    _inherit = 'account.move.line'

    def _check_invoice_related_move(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            if line.invoice:
                err_msg = _('Invoice name (id): %s (%s)') % (line.invoice.name, str(line.invoice.id))
                raise osv.except_osv(
                    _('Error!'), 
                    _('You cannot do this on an entry generated by an invoice. You must '
                    'change the related invoice directly.\n%s.') % err_msg)
        return True

    def _check_statement_related_move(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            if line.statement_id:
                err_msg = _('Bank statement name (id): %s (%s)') % (line.statement_id.name, str(line.statement_id.id))
                raise osv.except_osv(
                    _('Error!'), 
                    _('You cannot do this on an entry generated by a bank statement. '
                    'You must change the related bank statement directly.\n%s.') % err_msg)
        return True

    def unlink(self, cr, uid, ids, context=None, check=True):
        """ Add the verification of:
            - Is the move related to an invoice
            - Is the move related to a bank statement
            In that case, we forbid the move to be deleted even if draft. We should
            never delete directly a move line related or generated by another object.
            This is mandatory if you use the all move in draft (module: account_default_draft_move)
            """
        if not context.get('from_parent_object', False):
            self._check_invoice_related_move(cr, uid, ids, context=context)
            self._check_statement_related_move(cr, uid, ids, context=context)
        return super(AccountMoveLine, self).unlink(cr, uid, ids, context=context, check=check)

    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        """ Add the verification of:
            - Is the move related to an invoice
            - Is the move related to a bank statement
            In that case, we forbid the move to be modified even if draft. We should
            never update directly a move line related or generated by another object.
            This is mandatory if you use the all move in draft (module: account_default_draft_move)
            """
        if not context.get('from_parent_object', False):
            self._check_invoice_related_move(cr, uid, ids, context=context)
            self._check_statement_related_move(cr, uid, ids, context=context)
        return super(AccountMoveLine, self).write(cr, uid, ids, vals, 
            context=context, check=check, update_check=update_check)

    def _check_currency_and_amount(self, cr, uid, ids, context=None):
        for l in self.browse(cr, uid, ids, context=context):
            if ((l.currency_id and not l.amount_currency) or
                    (not l.currency_id and l.amount_currency)):
                return False
        return True

    def _check_currency_amount(self, cr, uid, ids, context=None):
        for l in self.browse(cr, uid, ids, context=context):
            if l.amount_currency:
                if ((l.amount_currency > 0.0 and l.credit > 0.0) or
                        (l.amount_currency < 0.0 and l.debit > 0.0)):
                    return False
        return True

    def _check_currency_company(self, cr, uid, ids, context=None):
        for l in self.browse(cr, uid, ids, context=context):
            if l.currency_id.id == l.company_id.currency_id.id:
                return False
        return True

    _constraints = [
            (_check_currency_and_amount,
             "You cannot create journal items with a secondary currency "
             "without recording both 'currency' and 'amount currency' field.",
             ['currency_id','amount_currency']
            ),
            (_check_currency_amount,
             "The amount expressed in the secondary currency must be positive "
             "when journal item are debit and negatif when journal item are "
             "credit.",
              ['amount_currency']
            ),
            (_check_currency_company,
             "You can't provide a secondary currency if "
             "the same than the company one.",
             ['currency_id']
            ),
        ]


class AccountInvoice(orm.Model):
    _inherit = "account.invoice"
    
    def action_cancel(self, cr, uid, ids, context=None):
        """Override the method to add the key 'from_parent_object' in
        the context. This is to allow to delete move line related to invoice
        through the buton cancel."""
        if context is None:
            context = {}
        context['from_parent_object'] = True
        return super(AccountInvoice, self).action_cancel(cr, uid, ids, context=context)


class AccountBankStatement(orm.Model):
    _inherit = "account.bank.statement"

    def button_cancel(self, cr, uid, ids, context=None):
        """Override the method to add the key 'from_parent_object' in
        the context. This is to allow to delete move line related to bank statement
        through the buton cancel."""
        if context is None:
            context = {}
        context['from_parent_object'] = True
        return super(AccountBankStatement, self).button_cancel(cr, uid, ids, context=context)

    def create_move_from_st_line(self, cr, uid, st_line_id, company_currency_id, st_line_number, context=None):
        """Add the from_parent_object key in context in order to be able to post the move."""
        if context is None:
            context = {}
        context['from_parent_object'] = True
        return super(AccountBankStatement, self).create_move_from_st_line(cr, uid, 
            st_line_id, company_currency_id, st_line_number, context=context)

