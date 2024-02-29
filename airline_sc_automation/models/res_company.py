# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta

class AirlineVisa(models.Model):
    _inherit = 'res.company'

    co_company_logo = fields.Binary()
    address_image = fields.Binary()

