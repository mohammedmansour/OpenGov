# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import time

from osv import fields, osv
from tools.translate import _
import psycopg2            # module to connect to postgresql
import sys 
import csv            # to read csv files
from subprocess import call    # to run system commands
from datetime import datetime, date

class hr_action_reason(osv.osv):
    _name = "hr.action.reason"
    _description = "Action Reason"
    _columns = {
        'name': fields.char('Reason', size=64, required=True, help='Specifies the reason for Signing In/Signing Out.'),
        'action_type': fields.selection([('sign_in', 'Sign in'), ('sign_out', 'Sign out')], "Action Type"),
    }
    _defaults = {
        'action_type': 'sign_in',
    }

hr_action_reason()

def _employee_get(obj, cr, uid, context=None):
    ids = obj.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
    return ids and ids[0] or False

class hr_attendance(osv.osv):
    _name = "hr.attendance"
    _description = "Attendance"

    def _day_compute(self, cr, uid, ids, fieldnames, args, context=None):
        res = dict.fromkeys(ids, '')
        for obj in self.browse(cr, uid, ids, context=context):
            res[obj.id] = time.strftime('%Y-%m-%d', time.strptime(obj.name, '%Y-%m-%d %H:%M:%S'))
        return res

    _columns = {
        'name': fields.datetime('Date', required=True, select=1),
        'action': fields.selection([('sign_in', 'Sign In'), ('sign_out', 'Sign Out'), ('action','Action')], 'Action', required=True),
        'day_type': fields.char('Day Type', size=64, help='Specifies if it is a working day or a holiday.'),
        'late': fields.char('Sign in Diff.', size=64, help='Specifies the lateness of the employee.'),
        'sign_state' : fields.char('Sign state', size=64),
        'overtime': fields.char('Sign out Diff.', size=64, help='Specifies the over time the employee will spend working.'),
        'action_desc': fields.many2one("hr.action.reason", "Action Reason", domain="[('action_type', '=', action)]", help='Specifies the reason for Signing In/Signing Out in case of extra hours.'),
        'employee_id': fields.many2one('hr.employee', "Employee's Name", required=True, select=True),
        'day': fields.function(_day_compute, type='char', string='Day', store=True, select=1, size=32),
    }
     
    def update(self,cr,uid,ids=None,context=None):
        mdb_path='/usr/share/pyshared/openerp/addons/hr_attendance/att2000.mdb'        # path to MS Access file 
        conversion_string="mdb-export %s CHECKINOUT | tail -n +2 | cut -d, -f1,2,3 | tr / - >/usr/share/pyshared/openerp/addons/hr_attendance/CHECKINOUT.csv"%mdb_path
        call(conversion_string,shell=True)    # getting the .csv file from .mdb file using {mdb-tools >> in Redhat/Centos/Fedora} || {mdbtools >> in Debian/Ubuntu
          
        i=1        # counter to count the number of errors, i.e, number of not inserted rows that mean the data is already exist
        table_name='hr_attendance'    # the table name to insert data 
        with open('/usr/share/pyshared/openerp/addons/hr_attendance/CHECKINOUT.csv','r') as f:
          re = csv.reader(f,delimiter=',',quoting=csv.QUOTE_NONE)
          for r in re:
            employee_id= int(r[0])
            name=r[1].replace('\"','')
            checktype=r[2].replace('\"','')
            
            if checktype == "I":
              action = "sign_in"
            else:
              action = "sign_out"
              
            try:
                cr.execute("insert into %s (employee_id, name, action, day) values(%d,'%s','%s',date('%s'))"%(table_name,employee_id,name,action,name))
            except psycopg2.DatabaseError, e:
                print 'error %d'%i
            i+=1
        
            

    def update_attendance(self,cr,uid,ids=None,context=None):
	fmt = '%Y-%m-%d %H:%M:%S'
	files_path ='/usr/share/pyshared/openerp/addons/hr_attendance/' 
	convert_mdb_to_csv = 'mdb-export ' + files_path +'att2000.mdb CHECKINOUT | tail -n +2 | cut -d, -f1,2,3 | tr / - > '+ files_path + ' CHECKINOUT.csv'
	call(convert_mdb_to_csv,shell=True)


	with open(files_path+'CHECKINOUT.csv','r') as f:
	  re = csv.reader(f, delimiter=',', quoting = csv.QUOTE_NONE)
	  for r in re:
	    employee_id = int(r[0])
	    name = r[1].replace('\"','')
	    checktype = r[2].replace('\"','') 

	    if checktype == "I":
	      action = "sign_in"
	    else:
	      action = "sign_out"
	    cr.execute("insert into hr_attendance (employee_id, name, action, day) values(%d,'%s','%s',date('%s'))"%(employee_id, name, action, name))
        cr.execute("select name from hr_attendance;")
        hr_attendance_day = cr.fetchall()

	  
	cr.execute("select att.employee_id, att.name, concat(holstat.name,' (', hol.name, ')') from hr_attendance as att, hr_holidays as hol, hr_holidays_status as holstat where hol.holiday_status_id = holstat.id and hol.type='remove' and hol.state='validate' and att.name between hol.date_from and hol.date_to and att.action='sign_in' and hol.employee_id = att.employee_id;")
	holiday_info = cr.fetchall()

	for days in hr_attendance_day:
	  day=datetime.strptime(days[0], fmt).weekday()
	  normal_or_weekend="select * from resource_calendar_attendance where dayofweek= '%d';"%(day)
	  cr.execute(normal_or_weekend)
	  if cr.fetchall():
	    n_day = "update hr_attendance set day_type='Normal Day' where action='sign_in' and name='%s';"%(days[0])
	    cr.execute(n_day)
	  else:
	    w_day = "update hr_attendance set day_type='Weekend' where action='sign_in' and name='%s';"%(days[0])
	    cr.execute(w_day)

	for infos in holiday_info:
	  update_day_type= "update hr_attendance set day_type = '%s' where employee_id=%d and name='%s';"%(infos[2],infos[0],infos[1])
	  cr.execute(update_day_type)


	for actual_sign_in_times in hr_attendance_day:
	  actual_sign_in_day_number=datetime.strptime(actual_sign_in_times[0], fmt).weekday()
	  get_supposed_sign_in_time = "select hour_from from resource_calendar_attendance where dayofweek='%s'"%(actual_sign_in_day_number)
	  cr.execute(get_supposed_sign_in_time)
	  supposed_sign_in = cr.fetchall()

	  for supposed_sign_in_times in supposed_sign_in:
	    actual_sign_in_date=datetime.strptime(actual_sign_in_times[0],fmt).date()
	    supposed_sign_in_date_and_time="%s %d:00:00"%(actual_sign_in_date,int(supposed_sign_in_times[0]))

	    supposed = datetime.strptime(supposed_sign_in_date_and_time,fmt)
	    actual = datetime.strptime(actual_sign_in_times[0], fmt)
	    
	    if actual > supposed:
	      sign_in_difference = actual-supposed
	      late = "update hr_attendance set late = '-%s', sign_state='late' where name='%s' and action='sign_in'"%(sign_in_difference, actual)
	    elif actual < supposed:
	      sign_in_difference = supposed-actual
	      late = "update hr_attendance set late = '%s' where name='%s' and action='sign_in'"%(sign_in_difference, actual)
	    cr.execute(late)
	  
	for actual_sign_out_times in hr_attendance_day:
	  actual_sign_out_time=datetime.strptime(actual_sign_out_times[0], fmt)
	  get_supposed_sign_out_time = "select hour_to from resource_calendar_attendance where dayofweek='%s'"%(actual_sign_out_time.weekday())
	  cr.execute(get_supposed_sign_out_time)
	  supposed_sign_out = cr.fetchall()


	  for supposed_sign_out_times in supposed_sign_out:
	    actual_sign_out_date=datetime.strptime(actual_sign_out_times[0],fmt).date()
	    supposed_sign_out_date_and_time="%s %d:00:00"%(actual_sign_out_date,int(supposed_sign_out_times[0]))

	    supposed = datetime.strptime(supposed_sign_out_date_and_time,fmt)
	    actual = datetime.strptime(actual_sign_out_times[0], fmt)
	    
	    if actual > supposed:
	      sign_out_difference = actual-supposed
	      late = "update hr_attendance set overtime = '%s' where name='%s' and action='sign_out'"%(sign_out_difference, actual)
	    elif actual < supposed:
	      sign_out_difference = supposed-actual
	      late = "update hr_attendance set overtime = '-%s', sign_state='leave_earlier' where name='%s' and action='sign_out'"%(sign_out_difference, actual)
	    cr.execute(late)
	   
            
            
    _sql_constraints = [
        ('name', 'UNIQUE(name)', 'The name of the category must be unique' )
    ]
    _defaults = {
        'name': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'), #please don't remove the lambda, if you remove it then the current time will not change
        'employee_id': _employee_get,
    }
    
   
    
   
    def _altern_si_so(self, cr, uid, ids, context=None):
        """ Alternance sign_in/sign_out check.
            Previous (if exists) must be of opposite action.
            Next (if exists) must be of opposite action.
        """
        for att in self.browse(cr, uid, ids, context=context):
            # search and browse for first previous and first next records
            prev_att_ids = self.search(cr, uid, [('employee_id', '=', att.employee_id.id), ('name', '<', att.name), ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='name DESC')
            next_add_ids = self.search(cr, uid, [('employee_id', '=', att.employee_id.id), ('name', '>', att.name), ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='name ASC')
            prev_atts = self.browse(cr, uid, prev_att_ids, context=context)
            next_atts = self.browse(cr, uid, next_add_ids, context=context)
            # check for alternance, return False if at least one condition is not satisfied
            if prev_atts and prev_atts[0].action == att.action: # previous exists and is same action
                return False
            if next_atts and next_atts[0].action == att.action: # next exists and is same action
                return False
            if (not prev_atts) and (not next_atts) and att.action != 'sign_in': # first attendance must be sign_in
                return False
        return True

    _constraints = [(_altern_si_so, 'Error: Sign in (resp. Sign out) must follow Sign out (resp. Sign in)', ['action'])]
    _order = 'name desc'

hr_attendance()

class hr_employee(osv.osv):
    _inherit = "hr.employee"
    _description = "Employee"

    def _state(self, cr, uid, ids, name, args, context=None):
        result = {}
        if not ids:
            return result
        for id in ids:
            result[id] = 'absent'
        cr.execute('SELECT hr_attendance.action, hr_attendance.employee_id \
                FROM ( \
                    SELECT MAX(name) AS name, employee_id \
                    FROM hr_attendance \
                    WHERE action in (\'sign_in\', \'sign_out\') \
                    GROUP BY employee_id \
                ) AS foo \
                LEFT JOIN hr_attendance \
                    ON (hr_attendance.employee_id = foo.employee_id \
                        AND hr_attendance.name = foo.name) \
                WHERE hr_attendance.employee_id IN %s',(tuple(ids),))
        for res in cr.fetchall():
            result[res[1]] = res[0] == 'sign_in' and 'present' or 'absent'
        return result

    _columns = {
       'state': fields.function(_state, type='selection', selection=[('absent', 'Absent'), ('present', 'Present')], string='Attendance'),
    }

    def _action_check(self, cr, uid, emp_id, dt=False, context=None):
        cr.execute('SELECT MAX(name) FROM hr_attendance WHERE employee_id=%s', (emp_id,))
        res = cr.fetchone()
        return not (res and (res[0]>=(dt or time.strftime('%Y-%m-%d %H:%M:%S'))))

    def attendance_action_change(self, cr, uid, ids, type='action', context=None, dt=False, *args):
        obj_attendance = self.pool.get('hr.attendance')
        id = False
        warning_sign = 'sign'
        res = {}

        #Special case when button calls this method: type=context
        if isinstance(type, dict):
            type = type.get('type','action')
        if type == 'sign_in':
            warning_sign = "Sign In"
        elif type == 'sign_out':
            warning_sign = "Sign Out"
        for emp in self.read(cr, uid, ids, ['id'], context=context):
            if not self._action_check(cr, uid, emp['id'], dt, context):
                raise osv.except_osv(_('Warning'), _('You tried to %s with a date anterior to another event !\nTry to contact the administrator to correct attendances.')%(warning_sign,))

            res = {'action': type, 'employee_id': emp['id']}
            if dt:
                res['name'] = dt
        id = obj_attendance.create(cr, uid, res, context=context)

        if type != 'action':
            return id
        return True

hr_employee()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
