# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_vendor = fields.Boolean(string="Tickets Vendor")
    ticket_number_is_required = fields.Boolean(string="Required TN?")
    is_tour_vendor = fields.Boolean(string="Tours Vendor")
    is_visa_vendor = fields.Boolean(string="Visa Vendor")
    is_mpayment_vendor = fields.Boolean(string="MPayment Vendor")
    is_hotel  = fields.Boolean(string="Hotel")
    is_airport = fields.Boolean(string="Airport")
    tickets_number = fields.Integer(compute = "_compute_tickets_number")
    id_number = fields.Char()
    airline_currency_id = fields.Many2one('res.currency', default = lambda self: self.env.user.company_id.currency_id.id, track_visibility='always', string="Vendor Currency", required=True)


    def create_crm_ticket(self):
        view_id = self.env.ref('crm.crm_lead_view_form').id
        return {
            'name': 'New CRM Ticket',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'target': 'current',
            'context': {
                'default_partner_id': self.id,
                'default_email_from': self.email,
                'default_phone': self.phone,
                'form_view_initial_mode': 'edit', 
                'force_detailed_view': 'true'
            },
        }


    def create_helpdesk_ticket(self):
        view_id = self.env.ref('helpdesk.helpdesk_ticket_view_form').id
        return {
            'name': 'New Helpdesk Ticket',
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'target': 'current',
            'context': {
                'default_partner_id': self.id,
                'default_partner_email': self.email,
                'default_partner_phone': self.phone,
                'form_view_initial_mode': 'edit', 
                'force_detailed_view': 'true'
            },
        }
    

    def _compute_tickets_number(self):
        for rec in self:
            rec.tickets_number = self.env['airline.ticket'].search_count([('customer_id', '=', rec.id)])

    def action_create_ticket(self):
        return {
            'name': f'New Ticket for {self.name}',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_model': 'airline.ticket',
            'context': {
                'default_customer_id': self.id,
                'default_readonly_customer': True,
            },
        }
    

    def action_create_visa(self):
        return {
            'name': f'New Visa for {self.name}',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_model': 'airline.visa',
            'context': {
                'default_customer_id': self.id,
                'default_readonly_customer': True,
            },
        }
    

    def action_create_mpayment(self):
        return {
            'name': f'New MPayment for {self.name}',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_model': 'airline.mpayment',
            'context': {
                'default_customer_id': self.id,
                'default_readonly_customer': True,
            },
        }
    
    def action_create_tour(self):
        return {
            'name': f'New Tour for {self.name}',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_model': 'airline.tour',
            'context': {
                'default_customer_id': self.id,
                'default_readonly_customer': True,
            },
        }
    
    
    def action_view_tickets(self):
        return {
            'name': f'{self.name} Tickets',
            'view_mode': 'tree,form',
            'domain': [('customer_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'res_model': 'airline.ticket',
            'target': 'current',
        }