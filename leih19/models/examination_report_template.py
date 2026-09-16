import re

from odoo import api, fields, models


class ExaminationReportTemplate(models.Model):
    _name = 'examination.report.template'
    _description = 'Examination Report Template (descriptive)'
    _order = 'name'

    name = fields.Char('Template Name', required=True)
    report_type = fields.Selection(
        [('radiology', 'Radiology'),
         ('descriptive', 'Descriptive (USG/Echo/etc.)'),
         ('pathology', 'Pathology'),
         ('other', 'Other')],
        string='Report Type', default='descriptive', required=True,
    )
    body_html = fields.Html('Body', sanitize=False)
    department = fields.Many2one('diagnosis.department', string='Department')
    examination_entry_ids = fields.Many2many(
        'examination.entry', 'examination_entry_template_rel',
        'template_id', 'examination_entry_id',
        string='Applies to Tests',
    )
    active = fields.Boolean(default=True)
    note = fields.Char('Note')

    # ------------------------------------------------------------------
    # Plain film template routing
    # ------------------------------------------------------------------
    # Which template a plain film should open with, decided by what the study
    # calls itself. Ordered most specific first: a barium study of the spine is
    # a contrast study, and a chest film naming a rib is still a chest film.
    _PLAIN_FILM_ROUTING = [
        ('xray_tpl_contrast', r'barium|ba-\s*meal|ba-\s*follow|ba-\s*enema|sialogram|'
                              r'urethrogram|cystogram|cystourethrogram|pyelograph|i\.?\s*v\.?\s*u|'
                              r'cologram|loopogram|loopgram|myelogram|fistulogram|sinugram|'
                              r'genitogram|cloacogram|coanagram|choanogram|dacrocystogram|'
                              r'nephrostogram|hysterosalpingograph|o\.?c\.?g|t-tube|'
                              r'defecograph|phonogram|invertogram|contrast'),
        ('xray_tpl_chest',    r'\bchest\b|\bcxr\b|\bcrx\b|\brib\b|\bribs\b|thorax|sternum|'
                              r'\bclavicle\b|\bclavical\b|\bapical\b|lordotic'),
        ('xray_tpl_skull',    r'skull|mandible|maxilla|nasal|orbit|p\.?\s*n\.?\s*s|sinus|'
                              r'mastoid|zygomat|facial|towne|t\.?\s*m\.?\s*joint|styloid|'
                              r'sella|jaw|occlusal|acoustic|auditory|optic foramen|'
                              r'submento|perorbital|per-orbital|i\.\s*a\.\s*m|\bopg\b|\bface\b|\bear\b'),
        ('xray_tpl_spine',    r'spine|spinal|cervical|dorsal|lumb|sacro|sacral|coccyx|'
                              r'scoliogram|atlanto|s\.?\s*i\.?\s*joint|scanogarm|scanogram'),
        ('xray_tpl_abdomen',  r'abdomen|\bkub\b|abdominal'),
        ('xray_tpl_extremity', r'joint|limb|\bhand\b|\bfoot\b|\bfeet\b|\bknee\b|shoulder|'
                               r'elbow|wrist|ankle|femur|tibia|fibula|humerus|forearm|'
                               r'scapula|\bhip\b|pelvis|thigh|\bleg\b|\barm\b|heel|calcaneum|'
                               r'calcaneus|finger|thumb|patella|bone age|mortise|scaphoid'),
    ]

    @api.model
    def _attach_plain_film_templates(self):
        """Give every X-Ray study the reporting template that fits it.

        A result opens with the first template attached to its test, so each
        study gets exactly one - attaching several would make which one loads
        depend on record order. Anything the routing does not recognise falls
        back to the generic template.

        Only empty tests are touched, so a template a radiologist attached by
        hand survives the next upgrade.
        """
        department = self.env['diagnosis.department'].search([('name', '=', 'X-Ray')], limit=1)
        if not department:
            return
        routing = []
        for xmlid, pattern in self._PLAIN_FILM_ROUTING:
            template = self.env.ref('leih19.%s' % xmlid, raise_if_not_found=False)
            if template:
                routing.append((template, re.compile(pattern, re.I)))
        generic = self.env.ref('leih19.xray_tpl_generic', raise_if_not_found=False)
        if not generic:
            return

        for entry in self.env['examination.entry'].search([('department', '=', department.id)]):
            if entry.report_template_ids:
                continue
            name = entry.name or ''
            chosen = generic
            for template, pattern in routing:
                if pattern.search(name):
                    chosen = template
                    break
            entry.report_template_ids = [(4, chosen.id)]
            if not chosen.department:
                chosen.department = department
