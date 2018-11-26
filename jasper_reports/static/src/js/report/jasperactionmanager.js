// © 2018 Songpon Phusing
// License AGPL-3.0 or later (https://www.gnuorg/licenses/agpl.html).
odoo.define('report_jasper.report', function(require){
    'use strict';

    var ActionManager= require('web.ActionManager');
    var crash_manager = require('web.crash_manager');
    var framework = require('web.framework');
    var session = require('web.session');
    ActionManager.include({

        _executeReportAction: function (action, options){
            var self = this;
            var cloned_action = _.clone(action);
            if (cloned_action.report_type === 'jasper') {
                framework.blockUI();

                // _makeReportUrls COPY
                var report_jasper_url = 'report/jasper/' + cloned_action.report_name; // <<
                if (_.isUndefined(cloned_action.data) ||
                    _.isNull(cloned_action.data) ||
                    (_.isObject(cloned_action.data) && _.isEmpty(cloned_action.data)))
                {
                    if(cloned_action.context.active_ids) {
                        report_jasper_url += '/' + cloned_action.context.active_ids.join(',');
                    }
                } else {
                    report_jasper_url += '?options=' + encodeURIComponent(JSON.stringify(cloned_action.data)); // <<
                    report_jasper_url += '&context=' + encodeURIComponent(JSON.stringify(cloned_action.context)); // <<
                }

                // _downloadReport COPY
                var def = $.Deferred();
                var blocked  = !session.get_file({
                    url: report_jasper_url, // << replace
                    data: {data: JSON.stringify([
                            report_jasper_url,
                            cloned_action.report_type
                    ])},
                    error: crash_manager.rpc_error.bind(crash_manager),
                    success: function (){
                        if(cloned_action && options && !cloned_action.dialog){
                            options.on_close();
                        }
                    }
                });
                if (blocked) {
                    // AAB: this check should be done in get_file service directly,
                    // should not be the concern of the caller (and that way, get_file
                    // could return a deferred)
                    var message = _t('A popup window with your report was blocked. You ' +
                                     'may need to change your browser settings to allow ' +
                                     'popup windows for this page.');
                    this.do_warn(_t('Warning'), message, true);
                }
                //return def;

                framework.unblockUI();
                return def;
            }
            return self._super(action, options);
        }
    });
    });

