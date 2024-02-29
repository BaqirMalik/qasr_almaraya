# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class AccountPayment(models.Model):
    _inherit = "account.payment"

    source_info = fields.Html(string="Source Document Info", compute="_compute_source_info")
    ticket_ids = fields.Many2many('airline.ticket', compute="_compute_ticket_ids")
    tickets_count = fields.Integer(compute='_compute_ticket_ids')


    def action_draft(self):
        if not self.env.user.has_group('airline_sc_automation.group_reset_payment'):
            raise UserError("You can't reset payments to draft. please contact your administrator and request this action.")
        return super().action_draft()



    def _compute_ticket_ids(self):
        for rec in self:
            if rec.partner_type == 'customer' and rec.is_internal_transfer == False:
                rec.ticket_ids = self.env['airline.ticket'].search([]).filtered(lambda ticket: ticket.invoice_id.id in rec.reconciled_invoice_ids.ids)
                rec.tickets_count = len(rec.ticket_ids)
            else:
                rec.ticket_ids = False
                rec.tickets_count = 0


    def _compute_source_info(self):
        for rec in self:
            html_info = ""
            for ticket_id in rec.ticket_ids:
                html_info += f"<td>PNR: {ticket_id.pnr}<td/>"
                html_info += f"<td>, Vendor: {ticket_id.vendor_id.name}<td/>"
                html_info += f"<td>, Route: {ticket_id.source_id.code} → {ticket_id.destination_id.code}<td/>"
                str_date = f"{ticket_id.first_flight_date.strftime('%Y/%m/%d %H:%M')} → {ticket_id.second_flight_date.strftime('%Y/%m/%d %H:%M')}" if ticket_id.second_flight_date else f"{ticket_id.first_flight_date.strftime('%Y/%m/%d %H:%M')}"
                html_info += f"<td>, Date: {str_date}<td/>"
                html_info = f"<tr>{html_info}<tr/>"
            html_info = f"<table>{html_info}<table/>"
            rec.source_info = html_info




    def button_open_tickets(self):
        return {
            'name': f'Tickets',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.ticket_ids.ids)],
            'type': 'ir.actions.act_window',
            'res_model': 'airline.ticket',
            'target': 'current',
        }

