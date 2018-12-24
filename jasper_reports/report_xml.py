# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008-2012 NaN Projectes de Programari Lliure, S.L.
#                         http://www.NaN-tic.com
# Copyright (C) 2013 Tadeus Prastowo <tadeus.prastowo@infi-nity.com>
#                         Vikasa Infinity Anugrah <http://www.infi-nity.com>
# Copyright (C) 2011-Today Serpent Consulting Services Pvt. Ltd.
#                         (<http://www.serpentcs.com>)
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import os
import base64
from xml.dom.minidom import getDOMImplementation

from odoo.exceptions import UserError
from odoo import api, fields, models, _

from . jasper_report import Report


src_chars = """ '"()/*-+?¿!&$[]{}@#`'^:;<>=~%,\\"""
src_chars = str.encode(src_chars, 'iso-8859-1')
dst_chars = """________________________________"""
dst_chars = str.encode(dst_chars, 'iso-8859-1')


class ReportXmlFile(models.Model):
    _name = 'ir.actions.report.xml.file'

    file = fields.Binary('File', required=True,
                         filters="*.jrxml,*.properties,*.ttf", )
    filename = fields.Char('File Name')
    report_id = fields.Many2one('ir.actions.report', 'Report',
                                ondelete='cascade')
    default = fields.Boolean('Default', default=True)

    @api.model
    def create(self, values):
        result = super(ReportXmlFile, self).create(values)
        ir_actions_report_obj = \
            self.env['ir.actions.report'].browse(values['report_id'])
        # Removed the update method for the call the create_action() of
        # ir.actions.report object
        ir_actions_report_obj.update()
        return result

    @api.multi
    def write(self, values):
        result = super(ReportXmlFile, self).write(values)
        for attachment in self:
            ir_actions_report_obj = self.env['ir.actions.report'].browse(
                [attachment.report_id.id])
            ir_actions_report_obj.update()
        return result


# Inherit ir.actions.report.xml and add an action to be able to store
# .jrxml and .properties files attached to the report so they can be
# used as reports in the application.


class ReportXml(models.Model):
    _inherit = 'ir.actions.report'

    jasper_output = fields.Selection([('html', 'HTML'), ('csv', 'CSV'),
                                      ('xls', 'XLS'), ('rtf', 'RTF'),
                                      ('odt', 'ODT'), ('ods', 'ODS'),
                                      ('txt', 'Text'), ('pdf', 'PDF')],
                                     'Jasper Output', default='pdf')
    jasper_file_ids = fields.One2many('ir.actions.report.xml.file',
                                      'report_id', 'Files', help='')
    jasper_model_id = fields.Many2one('ir.model', 'Model', help='')
    jasper_report = fields.Boolean('Is Jasper Report?')
    report_type = fields.Selection(selection_add=[("jasper", "Jasper")])

    @api.model
    def xrender_jasper(self, docids, data):
        cr, uid, context = self.env.args
        report_model_name = 'report.%s' % self.report_name
        self.env.cr.execute('SELECT id, model FROM '
                            'ir_act_report_xml WHERE '
                            'report_name = %s LIMIT 1',
                            (self.report_name,))
        record = self.env.cr.dictfetchone()
        report_model = self.search([('report_name', '=', report_model_name)])
        if report_model is None:
            raise UserError(_('%s model was not found' % report_model_name))
        data.update({'env': self.env, 'model': record.get('model')})
        r = Report(report_model_name, cr, uid, docids, data, context)
        return r.execute()

    @api.model
    def render_jasper(self, docids, data=None):
        # If the report is using a custom model to render its html, we must use it.
        # Otherwise, fallback on the generic html rendering.
        report_model_name = 'report.%s' % self.report_name
        report_model = self.env.get(report_model_name)


        data.update({
            'doc_ids': docids,
            'model': self.model,
            'env': self.env,
            'data_source': 'model',
            'jasper_output':data.get('jasper_output','pdf')
            # 'records':[], # fill by parser generate records
            # 'docs':[], # default browse report
        })

        # normally if report_model is not None , it's mean we have parser need to define
        # using report name by "report"+"module"+"report_name" > report.account.report_xxx_yyy
        if report_model is not None:
            data['data_source'] = 'records'
            data = report_model.get_report_values(docids, data)
        else:
            docs = self.env[self.model].browse(docids)

            data.update({
                'docs':docs,
            })
        r = Report(report_model_name,data )
        return r.execute()

    @api.model
    def _get_report_from_name(self, report_name):
        res = super(ReportXml, self)._get_report_from_name(report_name)
        if res:
            return res
        report_obj = self.env['ir.actions.report']
        qwebtypes = ['jasper']
        conditions = [('report_type', 'in', qwebtypes),
                      ('report_name', '=', report_name)]
        context = self.env['res.users'].context_get()
        return report_obj.with_context(context).search(conditions, limit=1)

    @api.model
    def create(self, values):
        if self._context and self._context.get('jasper_report'):
            values['model'] = \
                self.env['ir.model'].browse(values['jasper_model_id']).model
            values['type'] = 'ir.actions.report'
            values['report_type'] = 'jasper'
            values['jasper_report'] = True
        return super(ReportXml, self).create(values)

    @api.multi
    def write(self, values):
        if self._context and self._context.get('jasper_report'):
            if 'jasper_model_id' in values:
                values['model'] = \
                    self.env['ir.model'].browse(
                        values['jasper_model_id']).model

            values['type'] = 'ir.actions.report'
            values['report_type'] = 'jasper'
            values['jasper_report'] = True
        return super(ReportXml, self).write(values)

    @api.multi
    def update(self):
        if self._context is None:
            self._context = {}
        for report in self:
            has_default = False
            # Browse attachments and store .jrxml and .properties
            # into jasper_reports/custom_reportsdirectory. Also add
            # or update ir.values data so they're shown on model views.for
            # attachment in self.env['ir.attachment'].browse(attachmentIds)
            for attachment in report.jasper_file_ids:
                content = attachment.file
                file_name = attachment.filename
                if not file_name or not content:
                    continue
                path = self.save_file(file_name, content)
                if '.jrxml' in file_name and attachment.default:
                    if has_default:
                        raise UserError(_('There is more than one \
                                         report marked as default'))
                    has_default = True
                    report.write({'report_file': path})
                    report.create_action()
                if not has_default:
                    raise UserError(_('No report has been marked as default! \
                                     You need atleast one jrxml report!'))
            # Ensure the report is registered so it can be used immediately
            # register_jasper_report(report.report_name, report.model)
        return True

    def save_file(self, name, value):
        path = os.path.abspath(os.path.dirname(__file__))
        path += '/custom_reports/%s' % name

        with open(path, 'wb+') as f:
            f.write(base64.decodestring(value))
        path = 'jasper_reports/custom_reports/%s' % name
        return path

    def normalize(self, text):
        if isinstance(text, str):
            text = text.encode('utf-8')
        return text

    def unaccent(self, text):
        src_chars_list = [
            "'", "(", ")", ",", "/", "*", "-", "+", "?", "¿", "!",
            "&", "$", "[", "]", "{", "}", "@", "#", "`", "^", ":",
            ";", "<", ">", "=", "~", "%", "\\"]
        if isinstance(text, str):
            for src in src_chars_list:
                text = text.replace(src, "_")
        return text

    @api.model
    def generate_xml(self, pool, model_name, parent_node, document, depth,
                     first_call):
        if self._context is None:
            self._context = {}

        # First of all add "id" field
        field_node = document.createElement('id')
        parent_node.appendChild(field_node)
        value_node = document.createTextNode('1')
        field_node.appendChild(value_node)
        language = self._context.get('lang')
        if language == 'en_US':
            language = False

        # Then add all fields in alphabetical order
        model_fields = pool[model_name]._fields
        keys_list = model_fields.keys()

        # Remove duplicates because model may have fields with the
        # same name as it's parent
        keys_list = sorted(keys_list)

        for field in keys_list:
            name = False
            if language:
                # Obtain field string for user's language.
                name = self.env['ir.translation']._get_source(
                    '{model},{field}'.format(model=model_name, field=field),
                    'field', language)
            if not name:
                # If there's not description in user's language,
                # use default (english) one.
                name = model_fields[field].string
            if name:
                self.unaccent(name)
            # After unaccent the name might result in an empty string
            if name:
                name = '%s-%s' % (self.unaccent(name), field)
            else:
                name = field
            field_node = document.createElement(name.replace(' ', '_'))

            parent_node.appendChild(field_node)
            field_type = model_fields[field].type

            if field_type in ('many2one', 'one2many', 'many2many'):
                if depth <= 1:
                    continue
                comodel_name = model_fields[field].comodel_name
                self.generate_xml(pool, comodel_name, field_node, document,
                                  depth - 1, False)
                continue

            value = field
            if field_type == 'float':
                value = '12345.67'
            elif field_type == 'integer':
                value = '12345'
            elif field_type == 'date':
                value = '2009-12-31 00:00:00'
            elif field_type == 'time':
                value = '12:34:56'
            elif field_type == 'datetime':
                value = '2009-12-31 12:34:56'

            value_node = document.createTextNode(value)
            field_node.appendChild(value_node)

        if depth > 1 and model_name != 'Attachments':
            # Create relation with attachments
            field_node = document.createElement('Attachments-Attachments')
            parent_node.appendChild(field_node)
            self.generate_xml(pool, 'ir.attachment', field_node, document,
                              depth - 1, False)

        if first_call:
            # Create relation with user
            field_node = document.createElement('User-User')
            parent_node.appendChild(field_node)
            self.generate_xml(pool, 'res.users', field_node, document,
                              depth - 1, False)

            # Create special entries
            field_node = document.createElement('Special-Special')
            parent_node.appendChild(field_node)

            new_node = document.createElement('copy')
            field_node.appendChild(new_node)
            value_node = document.createTextNode('1')
            new_node.appendChild(value_node)

            new_node = document.createElement('sequence')
            field_node.appendChild(new_node)
            value_node = document.createTextNode('1')
            new_node.appendChild(value_node)

            new_node = document.createElement('subsequence')
            field_node.appendChild(new_node)
            value_node = document.createTextNode('1')
            new_node.appendChild(value_node)

    @api.model
    def create_xml(self, model, depth):
        if self._context is None:
            self._context = {}
        document = getDOMImplementation().createDocument(None, 'data', None)
        top_node = document.documentElement
        record_node = document.createElement('record')
        top_node.appendChild(record_node)
        self.generate_xml(self.env, model, record_node, document, depth, True)
        return top_node.toxml()
