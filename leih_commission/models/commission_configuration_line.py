from odoo import models, fields

class CommissionConfigurationLine(models.Model):
    _name = 'commission.configuration.line'
    _description = 'CommissionConfigurationLine'

    commission_configuration_line_ids = fields.Many2one('commission.configuration', string='Commission Configuration ID')
    department_id = fields.Many2one('diagnosis.department', string='Department')
    test_id = fields.Many2one('examination.entry', string='Test Name')
    base_price_applicable = fields.Boolean('Base Price Applicable')
    applicable = fields.Boolean('Applicable', default=True)
    line_method = fields.Selection(
        [('percentage', 'Percentage / Fixed'),
         ('margin', 'Margin over Base Price')],
        string='Method', default='percentage', required=True,
        help="Percentage / Fixed: a % (and/or fixed) for this department/test.\n"
             "Margin over Base Price: referrer keeps whatever the bill exceeds the base price "
             "(e.g. base 4000, billed 5000 -> 1000).")
    base_price = fields.Float('Base Price', help="Referrer's agreed base/floor price for this test "
                                                 "(used by the 'Margin over Base Price' method).")
    fixed_amount = fields.Float('Fixed Amount')
    variance_amount = fields.Float('Amount (%)')
    test_price = fields.Float('Test Fee')
    est_commission_amount = fields.Float('Commission Amount')
    max_commission_amount = fields.Float('Max Commission Amount')
