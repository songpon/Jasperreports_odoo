# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2018-Today Serpent Consulting Services Pvt. Ltd.
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

from odoo.addons.web.controllers import main as report
from odoo.http import content_disposition, route, request

import json


class ReportController(report.ReportController):
    @route()
    def report_routes(self, reportname, docids=None, converter=None, **data):
        if converter == 'jasper':
            report_jas = request.env[
                'ir.actions.report'
                ]._get_report_from_name(
                reportname)
            context = dict(request.env.context)
            if docids:
                docids = [int(i) for i in docids.split(',')]
            if data.get('options'):
                data.update(json.loads(data.pop('options')))
            if data.get('context'):
                # Ignore 'lang' here, because the context in data is the one
                # from the webclient *but* if the user explicitely wants to
                # change the lang, this mechanism overwrites it.
                data['context'] = json.loads(data['context'])
                if data['context'].get('lang'):
                    del data['context']['lang']
                context.update(data['context'])
            jasper = report_jas.with_context(
                context).render_jasper(docids, data=data)
            output_format =  jasper[1]
            output_file = jasper[0]
            output_filename = '%s.%s' % (str(report_jas.name),output_format,)

            ctypes={
                'csv':'text/csv',
                'xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'xls':'application/vnd.ms-excel',
                'pdf':'application/pdf',
                'doc':'application/msword',
                'docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'txt':'text/plain',
                'odt':'application/vnd.oasis.opendocument.text ',
                'ods':'application/vnd.oasis.opendocument.spreadsheet',
                'rtf':'application/rtf',
                'html':'text/html',
            }

            headers= [
                ('Content-Type', ctypes[output_format]),
                ('Content-Length', len(output_file)),
                ('Content-Disposition', content_disposition(output_filename))
            ]

            return request.make_response(output_file, headers=headers)
        return super(ReportController, self).report_routes(
            reportname, docids, converter, **data
        )
