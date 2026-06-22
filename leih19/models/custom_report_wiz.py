from odoo import models, fields

class CustomReportWiz(models.Model):
    _name = 'custom.report.wiz'
    _description = 'CustomReportWiz'

    date_from = fields.Date('From Date')
    date_to = fields.Date('TO Date')
