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

from osv import fields,osv
import datetime
import psycopg2            # module to connect to postgresql
import sys 
import csv            # to read csv files
from subprocess import call    # to run system commands
class Update(osv.osv_memory):
    _name = 'hr.attendance.update'
    _columns = {
            'db': fields.selection([('acess', 'MS Access'), ('oracle', 'Oracle'),('mysql','MySQL'),('postgres','Postgres')], "DataBase Type"),
            'path':fields.char('Access Path',size=200),
            'dbname':fields.char('DataBase Name',size=200),
            'username':fields.char('User Name',size=15),
            'password':fields.char('password',size=200,password="True"),
    }
    def update(self,cr,uid,ids=None,context=None):
        mdb_path='/usr/share/pyshared/openerp/addons/hr_attendance/att2000.mdb'        # path to MS Access file 
        conversion_string="mdb-export %s CHECKINOUT | tail -n +2 | cut -d, -f1,2,3 | tr / - >/usr/share/pyshared/openerp/addons/hr_attendance/CHECKINOUT.csv"%mdb_path
        call(conversion_string,shell=True)    # getting the .csv file from .mdb file using {mdb-tools >> in Redhat/Centos/Fedora} || {mdbtools >> in Debian/Ubuntu
        con=None        # Initialize no connection
        con = psycopg2.connect(database='iti', user='openerp')    # Connect to database named(test) with user(postgres)
        cur = con.cursor()   
        con2 = psycopg2.connect(database='iti', user='openerp')    # Connect to database named(test) with user(postgres)
        cur2 = con2.cursor()
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
                print 'error'
            con.commit()
Update()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
